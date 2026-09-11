# P03 workflow outlines

Build these in the pinned n8n instance after the dispatcher exists. Do not commit hand-written workflow JSON from an agent. Lifecycle: this spec, then editor or public API, then `make import`, e2e, `make export`, sanitize, lint.

Every workflow except the error handler sets Error Workflow to `[PLT] Error Handler` once that platform workflow exists.

Internal types after normalize: `customer.upsert`, `order.paid`, `repo.push`, `custom.*`. Envelope uses CloudEvents 1.0 names: `specversion`, `id`, `source`, `type`, `time`, `subject`, `data`. Mapping belongs in `code-snippets/normalize_event.js` (not written in this slice) with Vitest fixtures per source.

## [P03] Event Router

Trigger: Webhook from the Go dispatcher (not from Stripe or GitHub directly).

Auth: HMAC header from the dispatcher. Reject 401 if it does not match. Do not put the secret in node output.

Input: JSON `{ "inbox_id": "<uuid>", "source": "...", "external_event_id": "...", "event_type": "...", "source_ts": "...", "payload": { } }`. Payload may be fetched by id instead of inlined if it is large; pass ids, not blobs, when in doubt.

Nodes (intent order):
1. Verify internal signature (backend or Code using a tested snippet).
2. Normalize to the CloudEvents envelope (`normalize_event.js`).
3. Validate required envelope fields.
4. Switch on `type`.
5. Execute Workflow: `customer.upsert` / `order.paid` / `repo.push` / `unknown`.
6. Respond to Webhook 200 as soon as the event is accepted for handling.

Output to dispatcher: HTTP 200 means accepted. Non-2xx means the dispatcher increments attempts and backs off.

Error path: signature fail 401, invalid envelope 400, unknown type goes to Handler unknown (not an error). HTTP Request nodes (if any) need an explicit timeout.

## [P03] Handler customer.upsert

Trigger: When Executed by Another Workflow.

Input: envelope with `data` containing source, external customer id, name, email (hash before store), `source_ts`.

Nodes:
1. Load current `p03.customers` row for `(source, external_id)`.
2. If existing `last_source_ts` is newer or equal, log stale and skip the upsert.
3. Else upsert name, email_hash, data, `last_source_ts`.
4. Claim effect key `customer.upsert:{source}:{external_id}:crm` in `p03.processed_effects` (`INSERT ON CONFLICT DO NOTHING`). If no row returned, skip the CRM call.
5. HTTP Request to mock CRM, timeout set, retry policy explicit.
6. `UPDATE p03.inbox_events SET status = 'processed' WHERE id = $1 AND status = 'dispatched'`.

Error path: CRM 5xx/429/timeout classified; set inbox `failed` with `last_error`. Dispatcher schedules retry.

## [P03] Handler order.paid

Trigger: When Executed by Another Workflow.

Input: envelope for Stripe checkout completed or Shopify order paid, mapped to `order.paid`.

Nodes:
1. Compute `order_key` = `{source}:{order_id}`.
2. Insert `p03.fulfilment_requests` on `order_key` unique. Conflict means skip create.
3. Claim effect key `order.paid:{source}:{order_id}:notify` before notify. Skip notify if the key exists.
4. Notify via Mailpit (local) or the configured channel from settings, never a hardcoded address in the node.
5. Mark inbox `processed` with the same guarded update as customer.upsert.

Error path: same failed/retry as above. Replay of a processed event must not create a second fulfilment or a second email.

## [P03] Handler repo.push

Trigger: When Executed by Another Workflow.

Input: GitHub `push` mapped to `repo.push`. Identity is the GitHub delivery id.

Nodes:
1. Insert `p03.repo_events` on unique `delivery_id`.
2. Claim effect key `repo.push:{delivery_id}:notify`.
3. Post a short summary (repo, ref, commit count) to the notify channel.
4. Mark inbox processed.

Error path: failed + dispatcher retry. Duplicate delivery id is a no-op.

## [P03] Handler unknown

Trigger: When Executed by Another Workflow.

Input: envelope whose type is not routed.

Nodes:
1. `UPDATE inbox_events SET status = 'ignored'` for that id.
2. Log `event_type` and `source`. This is not an error and must not page.

## [P03] Retention Purge

Trigger: Schedule, daily (Europe/Helsinki).

Nodes:
1. Read retention days from settings (default 30).
2. `UPDATE p03.inbox_events SET payload = NULL WHERE received_at < now() - retention AND payload IS NOT NULL`.
3. Keep id, source, external_event_id, status, timestamps.

Do not DELETE inbox rows from this workflow. Do not log payload contents.
