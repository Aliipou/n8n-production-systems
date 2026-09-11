# P01 workflow specs

Specs only. Workflow JSON is not hand-written (AGENTS.md section 5). JSON is imported from a running pinned n8n instance after this outline is built there.

Error Workflow for every workflow below (except the platform error handler itself): `[PLT] Error Handler`.

No hardcoded URLs, thresholds, or addresses in nodes. Backend base URL and `INTERNAL_API_TOKEN` live in n8n credentials. Thresholds live in `backend/config/scoring.yaml`. Quiet hours, CRM provider, and owner email live in `p01.settings`.

## Workflow list (from spec)

| Workflow | Trigger | Responsibility |
|---|---|---|
| `[P01] Lead Intake` | Webhook `POST /webhook/p01/leads` | Validate, normalize, dedupe, store, respond |
| `[P01] Qualify Lead` | Sub-workflow | Enrich, classify, score, route |
| `[P01] CRM Sync` | Sub-workflow | Upsert contact and company, activity notes |
| `[P01] Sales Path` | Sub-workflow | Notify sales, draft email, enqueue review |
| `[P01] Email Approval Callback` | Sub-workflow (from review receiver) | Send approved email, schedule follow-ups |
| `[P01] Nurture Path` | Sub-workflow | Templated email only with consent |
| `[P01] Follow-up Scheduler` | Schedule, every 10 min | Send due follow-ups inside quiet-hours window |
| `[P01] Inbound Signals` | Webhook `POST /webhook/p01/signals/{type}` | Reply, booking, bounce |
| `[P01] Reconcile` | Schedule, hourly | Re-run leads stuck in `new` or `crm_sync_status = pending` |

## `[P01] Lead Intake`

### Trigger

- Type: Webhook
- Method: `POST`
- Path: `/webhook/p01/leads`
- Auth: Header Auth credential (same internal token pattern as other project webhooks)
- Response mode: respond from a later node (not immediately on receive). Do not return 2xx before the lead or the duplicate result is stored.

### Input (body)

Required:

- `email`
- `name`
- `message` (max 5000 characters)
- `consent_marketing` (boolean)

Optional:

- `company_name`
- `phone`
- `language` (`fi` / `sv` / `en` / `other`)
- `country`
- `website`
- `company_size`
- `industry`
- `budget_range`
- `timeline`
- `submission_id` (form-generated; if missing, derive sha256 of email, message, and 10-minute bucket)
- honeypot field (name chosen in the editor; must be empty for a real submission)

### Output (HTTP)

- `400` invalid payload: `{ "status": "invalid", "errors": [...] }`
- `401` missing or wrong webhook auth
- `200` duplicate: `{ "status": "duplicate", "lead_ref": "<uuid>" }`
- `202` accepted: `{ "status": "accepted", "lead_ref": "<uuid>" }`

### Nodes (intent names, in order)

1. **Validate payload**
   - Required fields present, `message` at most 5000 chars, honeypot empty.
   - Failure: respond `400` with error codes. Do not store.
   - Honeypot filled: do not signal the bot. Respond `202`, store the lead as `spam`, skip qualify. Covered later by F05; this outline treats it as a branch after validation.
2. **Normalize through backend**
   - HTTP Request to `POST /v1/leads/normalize` with Header Auth (`INTERNAL_API_TOKEN`).
   - Timeout set on the node. On HTTP error, route to classification (no silent continue).
   - Input: trimmed form fields. Output: `email_normalized`, flags, `phone_e164`, language hint.
3. **Claim idempotency key**
   - Insert into `ops.idempotency_keys` with `scope = p01.submission` and `key = submission_id` (or the derived hash).
   - Use `INSERT ... ON CONFLICT DO NOTHING RETURNING`.
   - If no row returned: respond `200` duplicate with `lead_ref` from the existing result payload, then stop.
4. **Upsert lead and insert submission**
   - Upsert `p01.leads` by `email_normalized`.
   - Insert `p01.submissions` (raw payload retained 90 days).
   - If the existing lead was `contacted` in the last 30 days, mark returning so qualify does not send a second first-contact email.
5. **Respond accepted**
   - HTTP `202` `{ "lead_ref": "<uuid>" }`.
6. **Log then call Qualify Lead**
   - Insert `ops.execution_log` (`project = p01`, `workflow = [P01] Lead Intake`, `correlation_id` set).
   - Execute Workflow `[P01] Qualify Lead` with `lead_id` / `lead_ref` only (no raw payload, no secrets).

### Error paths

- Invalid JSON or schema: `400`, nothing stored.
- Backend normalize 5xx/timeout: classify as transient, short retry on the HTTP node, then `[PLT] Error Handler` / DLQ. Do not respond 202 if nothing was stored.
- Backend 401: classify as auth, alert, no retry.
- Duplicate concurrent posts: unique constraint plus `ON CONFLICT DO NOTHING` so one submission side effect.
- Qualify Lead failure after 202: lead stays `status = new`; `[P01] Reconcile` picks it up. Do not lose the stored row.

### Settings

- Error Workflow: `[PLT] Error Handler`
- Sticky notes on the canvas: validate, normalize and store, respond, hand off.

### Not in this workflow

Scoring, LLM classification, CRM, email. Those belong to `[P01] Qualify Lead` and later workflows.

## `[P01] Qualify Lead`

### Trigger

- Type: When Executed by Another Workflow
- Caller: `[P01] Lead Intake` (and `[P01] Reconcile` for stuck `new` leads)
- Input schema: `lead_id` / `lead_ref`, `correlation_id`. No raw form payload, no secrets.

### Nodes (intent names, in order)

1. **Load lead**
   - Read `p01.leads` (and latest submission fields needed for score).
2. **Suppression check**
   - Lookup `p01.suppression_list` by `email_normalized`.
   - If suppressed: skip email paths later; still call CRM Sync.
3. **Enrich**
   - Skip when `is_free_mail` is true.
   - HTTP Request to `GET /v1/enrich?domain=` (endpoint lands in P01-T05). Timeout set.
   - Failure: continue with `unknown` values, warn log. Do not fail the workflow.
4. **Classify intent**
   - LLM (or mock-llm) with prompt `prompts/classify_lead.v1.md`, 30 s timeout, JSON schema validation.
   - One retry that includes the validation error.
   - After a second failure: set `llm_status = failed`, AI points stay 0.
   - Audit: `ops.audit_log` actor `llm` for classification.
5. **Score through backend**
   - HTTP Request to `POST /v1/score` with Header Auth (`INTERNAL_API_TOKEN`).
   - Body: company size, industry, budget, timeline, intent, `is_free_mail`, `llm_status`, optional `urgency_hint`. Never send a `route` field as an instruction; the backend ignores it.
   - Persist `score`, `score_breakdown`, `route` on the lead.
   - Audit: actor `system` for score.
6. **Route Switch**
   - Branches: `sales`, `nurture`, `archive`, `hr_forward`, `support_forward`.
   - `sales` calls `[P01] Sales Path`.
   - `nurture` calls `[P01] Nurture Path`.
   - `archive`, `hr_forward`, `support_forward`: notify as specified later; no first-contact LLM email.
7. **CRM Sync**
   - Always Execute Workflow `[P01] CRM Sync`.

### Error paths

- Enrichment 500 or timeout: continue (F06).
- LLM timeout or invalid JSON twice: deterministic score, `cap_route` nurture from scoring.yaml (F07).
- Score HTTP 5xx: retry short, then DLQ. Lead stays `new` for Reconcile.
- Score HTTP 401: no retry, alert.

### Settings

- Error Workflow: `[PLT] Error Handler`
- Sticky notes: suppress, enrich, classify, score, route.

## `[P01] CRM Sync`

### Trigger

- Type: When Executed by Another Workflow
- Input: `lead_id`, `correlation_id`.

### Nodes (intent names, in order)

1. **Read CRM provider**
   - Select `p01.settings` key `crm_provider`.
2. **Branch mock**
   - HTTP Request to the mock CRM (`/mock-crm/*` on the backend when `MOCK_CRM=true`, P01-T06).
   - Search by email, create or update contact and company, write activity notes.
   - Timeouts set. Transient errors: short Retry On Fail, then classification to DLQ with `retry_workflow_id` pointing at this workflow. Lead keeps `crm_sync_status = pending`.
3. **Branch hubspot**
   - Native HubSpot node: search by email, then create or update, associate company.
   - TODO(verify): HubSpot node parameters against the pinned n8n 2.x instance. CI uses `mock`. Manual test with a free developer account is documented later.
4. **Already contacted**
   - Existing contact with an owner and activity in the last 30 days: set `already_contacted`, block automated email, notify the owner.
5. **Write CRM ids**
   - Update `p01.leads.crm_id` and `crm_sync_status`.

### Error paths

- CRM 500 or timeout: short retries, then DLQ (F09).
- CRM 429 with Retry-After: wait as instructed (F10). Node retry settings must honour Retry-After. TODO(verify) against the HTTP Request node in the pinned n8n version.
- CRM 401: no retry, alert, leads stay pending (F11).

### Settings

- Error Workflow: `[PLT] Error Handler`

## `[P01] Sales Path`

### Trigger

- Type: When Executed by Another Workflow
- Input: `lead_id`, `correlation_id`.

### Nodes (intent names, in order)

1. **Notify sales**
   - Execute `[PLT] Notify` with name, company, score breakdown, summary, CRM link.
   - No secrets in the payload.
2. **Draft first email**
   - LLM with prompt `prompts/first_email.v1.md`.
   - Allowed facts only: lead message, company name, enrichment industry and size, sender signature.
   - Rules: at most 120 words, lead's language, no prices, no promises, no invented facts.
   - Output `{subject, body, facts_used[]}`.
3. **Check draft**
   - HTTP Request `POST /v1/email/check` (P01-T07). Timeout set.
   - Failure: do not enqueue review with an invalid draft; classify and DLQ or flag for a person.
4. **Insert review row**
   - Insert `ops.review_queue` (`kind = lead_email_approval`, callback `[P01] Email Approval Callback`).
   - Set email_messages status `pending_approval`.
5. **Stop**
   - No Wait node. The review-ui and `[PLT] Review Decision Receiver` resume via the callback workflow.

### Error paths

- LLM draft invalid after retry: no email, audit, lead stays qualified without send.
- Notify failure: classify, do not block the review insert if the draft is valid (notify can retry via DLQ). Confirm this split when building.

### Settings

- Error Workflow: `[PLT] Error Handler`
- Sticky notes: notify, draft, review enqueue.

## `[P01] Email Approval Callback`

### Trigger

- Type: When Executed by Another Workflow (from `[PLT] Review Decision Receiver`)
- Input: review decision (`approved` or `rejected`), optional edited body, `review_id`, `lead_id`.

### Nodes (intent names)

**Approved (possibly edited)**

1. Suppression check again.
2. Set message status `sending`.
3. Send via SMTP with `List-Unsubscribe` header. Store `smtp_message_id`. Set `sent`. Mark lead `contacted` only after send succeeds.
4. Schedule follow-ups in `p01.followups`.
5. Add CRM activity.
6. Audit with the human actor.

**Rejected**

1. Set message status `rejected`.
2. Audit.
3. Optional note to the owner.

### Error paths

- SMTP down: message stays unsent, retried via DLQ, never sent twice (F18). Idempotency key is `email_messages.id`.
- Suppressed after approval: do not send.

### Settings

- Error Workflow: `[PLT] Error Handler`

## `[P01] Nurture Path`

### Trigger

- Type: When Executed by Another Workflow
- Input: `lead_id`, `correlation_id`.

### Nodes (intent names, in order)

1. **Consent check**
   - Continue only if `consent_marketing` is true and the address is not suppressed.
2. **Templated email only**
   - No LLM body. Render a stored template in the lead's language.
3. **Enqueue or send**
   - Same human-approval rule as sales for the first automated email unless settings say otherwise. Spec: first LLM email always needs approval; nurture is templated. Do not auto-send LLM text. Confirm send vs review when building.
4. **CRM Sync already called** by Qualify; add a nurture activity note if needed.

### Error paths

- No consent or suppressed: stop, no mail.
- SMTP: same as approval callback (no double send).

### Settings

- Error Workflow: `[PLT] Error Handler`

## `[P01] Follow-up Scheduler`

### Trigger

- Type: Schedule
- Interval: every 10 minutes

### Nodes (intent names, in order)

1. **Claim due rows**
   - `SELECT ... FROM p01.followups WHERE status = 'scheduled' AND due_at <= now() FOR UPDATE SKIP LOCKED LIMIT 100`.
2. **Cancel if terminal**
   - Cancel when the lead is replied, booked, unsubscribed, bounced, or suppressed. Set `cancel_reason`.
3. **Quiet hours**
   - Send only on weekdays between 08:00 and 18:00 Europe/Helsinki (from `p01.settings` `quiet_hours`).
   - Outside the window: move `due_at` to the next window. Do not Wait.
4. **Render and send**
   - Templated follow-up in the lead's language. Send, set `sent`, schedule the next step or finish.
5. **Log**
   - `ops.execution_log` with `correlation_id`.

### Error paths

- SMTP failure: row stays scheduled or moves through DLQ without a second successful send (idempotent message id).
- Claim race: `SKIP LOCKED` so two workers do not send the same step.

### Settings

- Error Workflow: `[PLT] Error Handler`
- Do not use Wait nodes for the 3-day / 7-day delays.

## `[P01] Inbound Signals`

### Trigger

- Type: Webhook
- Method: `POST`
- Path: `/webhook/p01/signals/{type}` with `type` in `reply`, `booking`, `bounce`
- Auth: Header Auth per source

### Input

- Booking: payload modelled on a common scheduling tool, fixture only.
- Reply: simulated parsed inbound email.
- Bounce: provider-style fixture.
- Unsubscribe is the backend HMAC page (`GET /v1/unsubscribe/{token}`), not this webhook.

### Nodes (intent names, in order)

1. **Validate auth and payload**
   - 401 on bad auth. 400 on invalid body.
2. **Load lead**
   - By email or id from the fixture.
3. **Update status**
   - Reply or booking: cancel follow-ups, update CRM, notify owner (F15).
   - Bounce: status `bounced`, suppression row, cancel follow-ups (F13).
4. **Respond 202** after durable writes.

### Error paths

- Unknown lead: 404 or 202 with no-op, chosen when building; must be tested.
- CRM update failure: DLQ, local status still updated.

### Settings

- Error Workflow: `[PLT] Error Handler`

## `[P01] Reconcile`

### Trigger

- Type: Schedule
- Interval: hourly

### Nodes (intent names, in order)

1. **Select stuck leads**
   - `status = 'new'` or `crm_sync_status = 'pending'`.
2. **Re-run Qualify or CRM Sync**
   - Execute the matching sub-workflow with `lead_id` only.
   - Idempotent steps: no second first-contact email, no second CRM create for the same email.
3. **Log**
   - Used after worker kill (F19). Chaos script `worker-kill-p01` is a later task.

### Error paths

- Sub-workflow failure: leave the row for the next hour. Do not create duplicate submissions.

### Settings

- Error Workflow: `[PLT] Error Handler`
