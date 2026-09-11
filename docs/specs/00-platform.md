# Spec 00: Platform Foundation (Phase 0)

Goal: the shared base every project uses. n8n in queue mode, databases, mock services, shared workflows, scripts, and CI. Nothing project-specific goes here.

Done when: `PLT-T13` passes in CI from a clean clone.

## 1. Services

`platform/compose/docker-compose.base.yml`. Projects add their own `docker-compose.yml` and are started with both files.

| Service | Purpose | Host port (127.0.0.1 only) |
|---|---|---|
| `postgres` | Databases `n8n` and `app` | 5432 |
| `redis` | n8n queue, rate limits, breaker state | 6379 |
| `migrate` | One-shot dbmate run for `ops` and project schemas | none |
| `n8n-main` | Editor, public API, webhooks | 5678 |
| `n8n-worker` (2 replicas) | Executes workflows | none |
| `mailpit` | SMTP sink and web UI | 1025, 8025 |
| `mock-llm` | OpenAI-compatible fake LLM | 8090 |
| `flaky-api` | Dependency with configurable failures | 8091 |
| `review-ui` | Human review queue and DLQ pages | 8092 |

Every service has a healthcheck. n8n starts after `postgres`, `redis`, and `migrate` are healthy or completed.

## 2. n8n configuration

Verify every variable name and default against the docs of the pinned version, then document each in `platform/compose/n8n.env.md` with the reason it is set.

- `DB_TYPE=postgresdb` and `DB_POSTGRESDB_*` pointing to database `n8n`.
- `EXECUTIONS_MODE=queue`, `QUEUE_BULL_REDIS_HOST=redis`.
- `N8N_ENCRYPTION_KEY` from `.env`, identical on main and workers.
- `OFFLOAD_MANUAL_EXECUTIONS_TO_WORKERS=true`.
- `N8N_METRICS=true`, plus the queue metrics option if the pinned version has one.
- `WEBHOOK_URL=http://localhost:5678/`.
- `GENERIC_TIMEZONE=Europe/Helsinki` and `TZ=Europe/Helsinki`.
- Execution pruning enabled with a documented maximum age. Failed executions are always saved.
- `N8N_DIAGNOSTICS_ENABLED=false` for local runs.
- Keep the 2.x security defaults: environment access from Code nodes blocked, Execute Command disabled.

Do:
- Confirm a test workflow actually runs on a worker (worker logs show the execution).
- Document the one-time owner account setup and API key creation for local use in `platform/README.md`.

Do not:
- Use SQLite, regular mode, or a single container.
- Put `N8N_ENCRYPTION_KEY` anywhere except `.env`.

## 3. Shared schema `ops` (database `app`)

`execution_log`
- `id bigserial pk`, `ts timestamptz not null default now()`, `correlation_id text not null`, `project text not null`, `workflow text not null`, `execution_id text`, `node text`, `level text check (level in ('debug','info','warn','error'))`, `event text not null`, `data jsonb`.
- Indexes: `(correlation_id)`, `(project, ts)`.

`idempotency_keys`
- `scope text`, `key text`, `first_seen_at timestamptz default now()`, `execution_id text`, `status text check (status in ('processing','done','failed'))`, `result jsonb`, primary key `(scope, key)`.

`dead_letter`
- `id uuid pk`, `project`, `workflow`, `dependency text`, `retry_workflow_id text`, `payload jsonb`, `error_class text`, `error_message text`, `attempts int`, `first_failed_at`, `last_failed_at`, `next_attempt_at timestamptz null`, `status text check (status in ('pending_retry','dead','replayed','discarded'))`, `replayed_execution_id text`.
- Index `(status, next_attempt_at)`.

`review_queue`
- `id uuid pk`, `project`, `kind text` (for example `lead_email_approval`, `invoice_review`), `subject_id text`, `payload jsonb`, `status text check (status in ('pending','approved','rejected','expired'))`, `created_at`, `decided_at`, `decided_by`, `decision jsonb`, `callback_workflow_id text`.
- Index `(status, created_at)`.

`audit_log`
- `id bigserial pk`, `ts`, `actor_type text check (actor_type in ('system','human','llm'))`, `actor_id`, `project`, `action`, `subject_type`, `subject_id`, `before jsonb`, `after jsonb`, `reason text`, `model text`, `prompt_version text`, `tokens_in int`, `tokens_out int`, `latency_ms int`.
- Application roles get INSERT and SELECT only.

`incidents` (used by P04)
- `id uuid pk`, `fingerprint text`, `title`, `severity`, `status text check (status in ('open','resolved'))`, `opened_at`, `resolved_at`, `details jsonb`.
- Partial unique index on `fingerprint` where `status = 'open'`.

Roles: `n8n_app` (used by the n8n Postgres credential, grants limited to `ops` and project schemas it needs), one role per backend service, `readonly` for dashboards.

## 4. Error taxonomy

Implemented twice with one shared fixture table so both give the same answer: `code-snippets/classify_error.js` (used in Code nodes) and `platform/libs/python/errors.py` (used by backends). A test loads `platform/libs/fixtures/error_cases.json` in both languages.

| Class | Signals | Default action |
|---|---|---|
| `transient` | HTTP 500, 502, 503, 504, timeouts, connection reset or refused, temporary DNS failure | Retry with backoff |
| `rate_limited` | HTTP 429, provider rate-limit error codes | Wait for `Retry-After` (capped), then retry |
| `invalid_data` | HTTP 400, 422, schema validation failure | Quarantine to review queue, no retry |
| `auth` | HTTP 401, 403 | Alert, open circuit for that dependency, no retry |
| `permanent` | HTTP 404, 410, 501, 409 on non-idempotent create | Dead letter, no retry |
| `unknown` | Anything else | Dead letter and alert |

Backoff: full jitter, base 2 s, cap 300 s, max 6 attempts. Configurable per dependency. A 409 on an idempotent create counts as success.

## 5. Shared workflows (`platform/workflows/`)

`[PLT] Error Handler`
- Error Trigger, then `Classify error` (snippet), then insert into `ops.execution_log` (level error), then insert into `ops.dead_letter` when the failed item is recoverable, then call `[PLT] Notify`.
- Notification dedupe: same workflow and error class within 10 minutes produce one message with a count.

`[PLT] Notify` (sub-workflow)
- Input: `severity`, `title`, `body`, `links[]`, `project`.
- Sends to Slack incoming webhook if configured in settings, otherwise email to Mailpit.
- Never includes payload fields that can contain personal data.

`[PLT] Review Decision Receiver`
- Webhook called by `review-ui` with an HMAC-signed body (verified by the review-ui shared secret through a backend check endpoint or Header Auth plus signature node, whichever the pinned version supports cleanly).
- Updates `ops.review_queue` only from `pending` (`UPDATE ... WHERE status = 'pending' RETURNING`). A second decision on the same item does nothing.
- Calls the workflow stored in `callback_workflow_id` with the decision.

`[PLT] DLQ Retrier`
- Schedule every minute. Claims up to 50 rows with `status = 'pending_retry' and next_attempt_at <= now()` using `FOR UPDATE SKIP LOCKED`.
- Calls `retry_workflow_id` with the stored payload. On failure computes the next attempt with backoff; after max attempts sets `dead` and notifies.

`[PLT] Heartbeat`
- Schedule every 5 minutes. Writes a `heartbeat` event. P04 alerts when it goes stale.

## 6. Mock services

`mock-llm` (FastAPI)
- OpenAI-compatible `POST /v1/chat/completions`, supports `response_format` with a JSON schema.
- Response chosen by sha256 of the normalized `(model, messages)` from `fixtures/llm/*.json` of the calling project. Without a fixture it returns a schema-valid deterministic default.
- Reports token counts. `POST /admin/mode` forces invalid JSON, timeouts, 429, or 500 for tests.
- Check whether the pinned n8n OpenAI credential accepts a custom base URL. If not, follow the fallback in `AGENTS.md` section 6.

`flaky-api` (Go)
- Generic JSON endpoints (`GET/POST/PUT /items`, `GET /items/{id}`) backed by memory.
- `POST /admin/mode` per route: `error_rate`, `status`, `latency_ms`, `retry_after_s`, `auth_fail`. `POST /admin/reset`.
- Counts requests per route (`GET /admin/stats`) so tests can assert "no hammering". Prometheus metrics at `/metrics`.

`review-ui` (FastAPI, Jinja templates, no SPA framework)
- Basic auth for local use. Lists pending items by kind, detail page per kind (templates added by projects), approve, reject, edit.
- On decision, posts a signed message to `[PLT] Review Decision Receiver` and writes an audit record.
- DLQ page added in P04.

## 7. Scripts

`sanitize_workflows.py`
- Removes `pinData`, `staticData`, `meta.instanceId`, and execution references.
- Sorts keys and formats with 2-space indentation and a trailing newline for stable diffs.
- Fails if any string matches secret patterns (gitleaks rules plus `sk-`, `xox`, `Bearer ` followed by a long token, private key headers).

`lint_workflows.py` fails on:
- `pinData` present.
- Default node names (regex for names such as `HTTP Request1`, `Code`, `Set2`, `IF`).
- Missing `settings.errorWorkflow` (except the error handler).
- HTTP Request nodes without a timeout option.
- Code nodes that declare a snippet marker (`// snippet: <name>`) but differ from `code-snippets/<name>.js`.
- More than 40 nodes.
- Hardcoded `http://` or `https://` URLs in node parameters other than credentials and settings lookups.
- Has its own tests with good and bad fixture workflows.

`sync_snippets.py`
- Replaces the body of every Code node that starts with `// snippet: <name>` with the file content.

`export_workflows.sh` and `import_workflows.sh`
- Use the n8n CLI inside the container (`export:workflow` with one file per workflow, `import:workflow`). Verify flags for the pinned version.
- Import also loads test credentials from `platform/ci/credentials.template.json` after environment substitution (mock endpoints and test tokens only), then publishes or activates imported workflows.

## 8. CI

As described in `docs/PLAN.md` section 9. The platform e2e job runs on every change to `platform/`, `scripts/`, or `code-snippets/`.

## 9. Documents created in Phase 0

- `README.md`: portfolio index with a table of projects, status, and links. Honest status labels ("in progress", "v1.0.0").
- `docs/PROGRESS.md`, `docs/QUESTIONS.md`.
- ADRs: `0001-monorepo`, `0002-n8n-orchestrates-backends-compute`, `0003-community-edition-only`, `0004-durable-scheduling-instead-of-long-waits`, `0005-error-taxonomy`.
- `.github/pull_request_template.md` with the DoD checklist.
- `LICENSE` (MIT for this repository's code) and `NOTICE` explaining that n8n itself is under its own licence and is not redistributed here.

## 10. Tasks

| ID | Task | Output |
|---|---|---|
| PLT-T01 | Scaffold layout, `.gitignore`, `.editorconfig`, LICENSE, NOTICE, pre-commit, Makefile skeleton | Repo skeleton |
| PLT-T02 | Look up current stable versions and pin them in `VERSIONS.md`; read n8n 2.0 breaking changes | `VERSIONS.md` with links |
| PLT-T03 | Base compose: postgres, redis, n8n main and 2 workers, healthchecks; prove execution on a worker | Running stack |
| PLT-T04 | `ops` migrations, roles, grants, append-only audit | Migrations and a test that UPDATE on audit fails |
| PLT-T05 | Mailpit and `mock-llm` with tests | Service and tests |
| PLT-T06 | `flaky-api` with tests | Service and tests |
| PLT-T07 | Sanitizer, linter, snippet sync, import and export scripts, with tests | Scripts and fixtures |
| PLT-T08 | Error taxonomy in JS and Python with shared fixtures | Both implementations agree |
| PLT-T09 | `[PLT] Error Handler` and `[PLT] Notify` | Workflows |
| PLT-T10 | `review-ui` skeleton and `[PLT] Review Decision Receiver` | Approve and reject work end to end |
| PLT-T11 | `[PLT] DLQ Retrier` and `[PLT] Heartbeat` | Workflows |
| PLT-T12 | CI pipelines and branch protection instructions | Green pipeline |
| PLT-T13 | Platform e2e: a workflow calling `flaky-api` in 500 mode fails, lands in DLQ, notification appears in Mailpit, flaky-api healed, DLQ Retrier recovers it, exactly one successful call recorded | Passing test |
| PLT-T14 | Portfolio README index, ADRs, PROGRESS, QUESTIONS | Docs |

## 11. Do and do not

Do:
- Keep the platform small. If only one project needs it, it belongs in that project.
- Make `make up` print the URLs of every UI (n8n, Mailpit, review UI) when ready.

Do not:
- Add Grafana or Prometheus here. They arrive in P04.
- Build a generic "framework" around n8n. Shared workflows plus a few scripts are enough.
