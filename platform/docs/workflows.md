# Platform workflows

Spec for PLT-T09, PLT-T10 (receiver), and PLT-T11. n8n orchestrates; Postgres and the mock services hold state.

Do not commit workflow JSON until AGENTS.md section 5 is complete: build in the pinned local n8n (`n8nio/n8n:2.37.9`), `make import`, publish, pass `platform/tests/e2e`, then `make export` (sanitize and lint).

This Windows workspace has no Docker, so those steps are blocked. Node type versions and parameter shapes must come from that running instance. This file lists intent, order, inputs, outputs, and error paths only.

Error Workflow setting: every platform workflow except `[PLT] Error Handler` itself points at `[PLT] Error Handler`.

## Shared conventions

- Structured log rows go to `ops.execution_log` (`correlation_id`, `project`, `workflow`, `execution_id`). One HTTP Request (or Postgres node) per log write. Do not call a sub-workflow per log line.
- HTTP Request nodes: explicit timeout, named by intent, Retry On Fail for short transients or error output classified. No "Continue on fail" without handling.
- No hardcoded `http://` or `https://` in node parameters. Base URLs come from credentials or `ops` settings.
- Code nodes longer than 15 lines: `// snippet: classify_error` copied from `code-snippets/classify_error.js`.
- Secrets stay in credentials. Node outputs must not include tokens.

## `[PLT] Error Handler` (PLT-T09)

Trigger: Error Trigger.

Nodes in order:

1. Receive error payload from the failed execution.
2. `Classify error` (Code node, snippet `classify_error`).
3. Insert into `ops.execution_log` at level `error`.
4. If the class is recoverable for retry (`transient`, `rate_limited`): insert into `ops.dead_letter` with `status = pending_retry`, `attempts`, `next_attempt_at`, `retry_workflow_id`, payload without secrets.
5. If the class is `invalid_data`: do not retry. Quarantine is a project concern; here log and notify.
6. If the class is `auth`, `permanent`, or `unknown`: insert or update `ops.dead_letter` as `dead` when a payload exists, then notify.
7. Call `[PLT] Notify` with severity, title, body (no personal-data payload fields), project.

Notification dedupe: same workflow name and error class within 10 minutes produce one message with a count. Store the window in `ops` (settings or a small dedupe table). Do not use a Wait node for the window.

Error path: this workflow has no Error Workflow setting (it is the handler). If notify fails, log to `ops.execution_log` and stop. Do not recurse.

## `[PLT] Notify` (PLT-T09)

Trigger: When Executed by Another Workflow.

Input schema:

- `severity` (text)
- `title` (text)
- `body` (text)
- `links` (list of `{label, url}` where url comes from settings, not hardcoded)
- `project` (text)

Behaviour:

- If Slack incoming webhook is configured in settings, POST the message there (timeout set, no payload PII).
- Else send email through Mailpit (SMTP credential, not a hardcoded host in the node).
- Write `ops.execution_log` event `notify_sent` or `notify_skipped`.

Error path: Error Workflow = `[PLT] Error Handler`. Do not include the original failed payload in the notification body.

## `[PLT] Review Decision Receiver` (PLT-T10)

Trigger: Webhook (POST). Authenticate (Header Auth credential, or HMAC verified before a 2xx). Do not return 2xx before the decision row is stored.

Nodes in order:

1. Validate JSON body: `id`, `decision` (`approved` or `rejected`), optional `reason`, `actor`.
2. Verify HMAC (`X-Signature-256`) against the review-ui shared secret via the review-ui check endpoint or equivalent. 401 if invalid.
3. `UPDATE ops.review_queue SET status = $decision, decided_at = now(), decided_by = $actor, decision = $body WHERE id = $id AND status = 'pending' RETURNING *`.
4. If no row returned: 200 with `{status: "already_decided"}` and stop (idempotent second click).
5. Insert `ops.audit_log` (actor_type `human`).
6. If `callback_workflow_id` is set, Execute Workflow with the decision. Sub-workflow must be published (n8n 2.x).
7. Respond 200 with `{status: "accepted"}`.

Error path: Error Workflow = `[PLT] Error Handler`. Invalid JSON: 400 before any write.

## `[PLT] DLQ Retrier` (PLT-T11)

Trigger: Schedule every minute (`GENERIC_TIMEZONE=Europe/Helsinki`).

Nodes in order:

1. Claim up to 50 rows: `status = 'pending_retry' AND next_attempt_at <= now()` using `FOR UPDATE SKIP LOCKED`.
2. For each row, Execute Workflow `retry_workflow_id` with the stored payload.
3. On success: set `status = 'replayed'`, store `replayed_execution_id`, log.
4. On failure: increment `attempts`, set `next_attempt_at` with full jitter backoff (same constants as `code-snippets/classify_error.js` / `platform/libs/python/errors.py`). After max attempts, set `status = 'dead'` and call `[PLT] Notify`.

Do not use a Wait node for backoff. `next_attempt_at` is the wait.

Error path: Error Workflow = `[PLT] Error Handler`. A claim that fails mid-batch must not leave rows locked after the transaction ends.

## `[PLT] Heartbeat` (PLT-T11)

Trigger: Schedule every 5 minutes.

Nodes in order:

1. Insert `ops.execution_log` event `heartbeat` with `project = platform`, `workflow = [PLT] Heartbeat`.
2. Stop.

P04 alerts when this event goes stale. No Slack/email from this workflow.

Error path: Error Workflow = `[PLT] Error Handler`.

## `[PLT] Flaky Probe` (needed by PLT-T13, not a product workflow)

A small published workflow used only in local and CI e2e:

- Trigger: Webhook, Header Auth.
- Respond 202 after an idempotent insert (`ops.idempotency_keys`, `ON CONFLICT DO NOTHING RETURNING`).
- HTTP GET `flaky-api` `/items` (credential URL, timeout set).
- On success, log `probe_success`.
- On failure, let the Error Workflow run so the item lands in `ops.dead_letter` with `retry_workflow_id` pointing back at this workflow.

Build this in the same pinned instance as the other `[PLT]` workflows. Same import/export gate.

## Sticky notes (canvas)

Each section of each canvas must say what it does and what can fail there. Keep notes readable for README screenshots later.
