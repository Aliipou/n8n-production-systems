# P02 workflow specs

Specs only. Workflow JSON is not hand-written (AGENTS.md section 5). JSON is imported from a running pinned n8n instance after this outline is built there.

Error Workflow for every workflow below (except the platform error handler itself): `[PLT] Error Handler`.

No hardcoded URLs, thresholds, or addresses in nodes. doc-service base URL and `INTERNAL_API_TOKEN` live in n8n credentials. Auto-approve limits live in `backend/config/decision.yaml`. VAT rates live in `backend/config/vat_rates.yaml`. Files never pass through n8n; payloads carry `document_id` only.

## Workflow list (from spec)

| Workflow | Trigger | Responsibility |
|---|---|---|
| `[P02] Document Intake` | Webhook from doc-service | Idempotency on `document_id`, set processing, call Process |
| `[P02] Process Document` | Sub-workflow | Text, classify, extract, validate, decide, route |
| `[P02] Review Decision Callback` | Sub-workflow (from review receiver) | Apply corrections, audit, export |
| `[P02] Export` | Sub-workflow | Mock ERP create, idempotent |
| `[P02] Daily CSV Export` | Schedule, daily 06:00 | CSV of invoices approved the previous day |
| `[P02] Reconcile` | Schedule, every 15 min | Requeue documents stuck in `processing` over 10 minutes |
| `[P02] Retention Purge` | Schedule, daily | Delete files and text past retention, keep audit |

## `[P02] Document Intake`

### Trigger

- Type: Webhook
- Method: `POST`
- Path: `/webhook/p02/documents`
- Auth: Header Auth credential (same internal token pattern as other project webhooks)
- Response mode: respond from a later node (not immediately on receive). The file is already stored by doc-service before this webhook fires. Still do not return 2xx until the idempotency row exists.

### Input (body)

Required:

- `document_id` (uuid)
- `sha256` (hex)

No file bytes. No original filename required (doc-service already stored it).

### Output (HTTP)

- `400` invalid payload
- `401` missing or wrong webhook auth
- `200` duplicate: `{ "status": "duplicate", "document_id": "<uuid>" }`
- `202` accepted: `{ "status": "accepted", "document_id": "<uuid>" }`

### Nodes (intent names, in order)

1. **Validate payload**
   - `document_id` is a uuid, `sha256` is 64 hex chars.
   - Failure: respond `400`. Do not touch `p02.documents`.
2. **Claim idempotency key**
   - Insert into `ops.idempotency_keys` with `scope = p02.document` and `key = document_id`.
   - Use `INSERT ... ON CONFLICT DO NOTHING RETURNING`.
   - If no row returned: respond `200` duplicate, then stop. Do not call Process again.
3. **Set processing**
   - Update `p02.documents` set `status = processing` where `id = document_id` and `status = received`.
   - If the row is missing: classify as invalid, do not 202.
4. **Respond accepted**
   - HTTP `202` `{ "document_id": "<uuid>" }`.
5. **Log then call Process Document**
   - Insert `ops.execution_log` (`project = p02`, `workflow = [P02] Document Intake`, `correlation_id = document_id`).
   - Execute Workflow `[P02] Process Document` with `document_id` only.

### Error paths

- Invalid JSON or schema: `400`, nothing stored.
- Document id unknown: `400` or `404` (pick one in the editor and keep it), nothing processed.
- Duplicate concurrent webhooks: unique constraint plus `ON CONFLICT DO NOTHING` so Process runs once.
- Process failure after 202: status stays `processing`; `[P02] Reconcile` picks it up.

### Settings

- Error Workflow: `[PLT] Error Handler`
- Sticky notes on the canvas: validate, idempotency, respond, hand off.

### Not in this workflow

Text, OCR, LLM, validators, export. Those belong to `[P02] Process Document` and later workflows.

## `[P02] Process Document`

### Trigger

- Type: When Executed by Another Workflow
- Input: `{ "document_id": "<uuid>" }`

### Nodes (intent names, in order)

1. **Get text**
   - HTTP Request `POST /v1/documents/{id}/text` on doc-service (Header Auth, timeout set).
   - Encrypted or unreadable PDF: set `status = needs_manual`, enqueue review (`kind = unreadable_pdf`), audit, stop.
2. **Classify**
   - HTTP Request `POST /v1/documents/{id}/classify`.
   - Non-invoice: enqueue review (`kind = other_document`), stop.
3. **Rule extractors**
   - HTTP Request or Code node calling doc-service regex extractors for IBAN, Y-tunnus, reference, totals (later task). Keep this short; long logic stays in the backend.
4. **LLM extraction**
   - Prompt `prompts/extract_invoice.v1.md`, temperature 0, JSON schema, OpenAI-compatible base URL (mock-llm in CI).
   - Invalid output: one retry that includes the validation error. Second failure: review with rule-extracted fields prefilled.
5. **Validate**
   - HTTP Request `POST /v1/extractions/validate`. Persist rows in `p02.validations`.
6. **Decide**
   - HTTP Request `POST /v1/extractions/decide` (later task). Persist `p02.decisions`.
   - `auto_approve` only when config gates pass (all critical fields, all validators, known supplier, IBAN match, no duplicate, currency EUR, gross below limit, confidence at threshold).
   - IBAN mismatch, unknown supplier, and foreign currency never auto-approve.
7. **Route**
   - `auto_approve`: write `p02.invoices`, Execute Workflow `[P02] Export`.
   - `review`: insert `ops.review_queue` with reasons in plain language. IBAN mismatch includes a fraud warning flag for the UI.
8. **Audit**
   - Every status change writes `ops.audit_log` (`actor_type = system` or `llm` as appropriate).

### Error paths

- doc-service 5xx/timeout on text: short retry on the HTTP node, then Error Handler / DLQ. Leave status `processing` for Reconcile.
- LLM timeout twice: review, do not auto-approve.
- Prompt injection inside document text: no tools with side effects; decision still comes from validators (fixture in a later task).

### Settings

- Error Workflow: `[PLT] Error Handler`
- Sticky notes: text, classify, extract, validate and decide, route.

## `[P02] Review Decision Callback`

### Trigger

- Type: When Executed by Another Workflow (from `[PLT] Review Decision Receiver`)
- Input: review id, `document_id`, decision (`approved` / `rejected`), optional field corrections, reviewer id.

### Nodes (intent names, in order)

1. **Load review item**
   - Read `ops.review_queue` by id. Stop if already decided.
2. **Apply corrections**
   - Store a diff in `ops.audit_log`. Do not auto-add corrections to the evaluation set.
3. **Approve or reject**
   - Approve: write `p02.invoices` with `approved_by = reviewer id`, set document `approved`.
   - Reject: set document `rejected`, reason required.
4. **Call Export**
   - Only on approve. Execute Workflow `[P02] Export`.

### Error paths

- Duplicate callback: unique invoice `(supplier_id, invoice_number)` and export `(invoice_id, target)` prevent double side effects.
- IBAN still mismatched after approve: allowed only if the review payload includes the confirmation checkbox value. If missing, do not export.

## `[P02] Export`

### Trigger

- Type: When Executed by Another Workflow
- Input: `invoice_id`

### Nodes (intent names, in order)

1. **Load invoice**
   - Read `p02.invoices` and supplier registry fields needed by the mock ERP.
2. **Create in mock ERP**
   - HTTP Request to doc-service `/mock-erp/*` (enabled only when `MOCK_ERP=true`).
   - Idempotent on `(business_id, invoice_number)`.
   - Timeout set. 5xx: Retry On Fail short, then DLQ. 429: honour Retry-After via error classification (platform pattern).
3. **Record export**
   - Insert `p02.exports` (`target = erp_api`). Unique `(invoice_id, target)`.
   - Set document `exported`.

### Error paths

- Mock ERP 500: DLQ, retry, exactly one ERP record after recovery (e2e F15, later).
- Export row already sent: skip HTTP call, 200 from this sub-workflow.

## `[P02] Daily CSV Export`

### Trigger

- Type: Schedule
- Cron: `0 6 * * *` (06:00). Confirm timezone against the pinned n8n version (`TZ=Europe/Helsinki` on the stack).

### Nodes (intent names, in order)

1. **Select yesterday's approvals**
   - SQL: invoices approved the previous calendar day in Europe/Helsinki whose CSV export is missing.
2. **Write CSV**
   - Backend or a short Code node over already-fetched rows. File bytes stay in doc-service or a volume. n8n stores a path or export id, not the full CSV in execution data if it is large.
3. **Record export**
   - Insert `p02.exports` (`target = csv`) per invoice. Unique `(invoice_id, target)`.

### Error paths

- Empty set: log and stop, not an error.
- Partial write: do not mark `sent` until the file is on the volume.

## `[P02] Reconcile`

### Trigger

- Type: Schedule
- Every 15 minutes.

### Nodes (intent names, in order)

1. **Find stuck documents**
   - `p02.documents` where `status = processing` and `updated_at` older than 10 minutes.
2. **Requeue Process**
   - Execute Workflow `[P02] Process Document` with `document_id`.
   - Idempotent invoice and export constraints prevent duplicate side effects if Process had finished after the query.

### Error paths

- Worker kill mid-process: this workflow is the recovery path (chaos `worker-kill-p02`, later).

## `[P02] Retention Purge`

### Trigger

- Type: Schedule
- Daily (time chosen in the editor; document it on the sticky note).

### Nodes (intent names, in order)

1. **Select expired files**
   - Documents past the retention window in settings. Keep `p02.invoices`, `p02.exports`, and `ops.audit_log`.
2. **Delete text and bytes**
   - HTTP Request to doc-service to delete file bytes and `p02.document_text`. Then delete or anonymize `p02.documents` as specified in the later retention task.
3. **Audit**
   - Insert `ops.audit_log` with counts only, not file contents.

### Error paths

- Delete failure: do not remove the database pointer if the file is still on the volume. Retry next run.

### Not in any P02 workflow

Hand-written workflow JSON. Real invoices. Passing PDF bytes through n8n. Auto-approve on IBAN change, unknown supplier, or foreign currency.
