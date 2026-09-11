# Platform

Shared n8n queue-mode stack, `ops` schema, mock services, review-ui, and workflow scripts.

Compose: [compose/docker-compose.base.yml](compose/docker-compose.base.yml). Pins: [VERSIONS.md](VERSIONS.md). n8n variables: [compose/n8n.env.md](compose/n8n.env.md). Workflow specs: [docs/workflows.md](docs/workflows.md).

Services bind to `127.0.0.1` only. Do not publish ports on `0.0.0.0`.

n8n orchestrates. Python and Go services compute (error taxonomy, mock-llm, flaky-api, review-ui).

## What is in this folder

- Postgres 16, Redis 7.4, n8n main plus two workers (`n8nio/n8n:2.37.9`), Mailpit, mock-llm, flaky-api, review-ui
- dbmate migrations for schema `ops` (execution log, idempotency, dead letter, review queue, append-only audit)
- Sanitizer, linter, import/export, snippet sync (`scripts/` at the repo root)
- CI workflows named `lint`, `unit`, `secrets`, `e2e`

## What is not here yet

- Committed `[PLT]` workflow JSON (Error Handler, Notify, Review Decision Receiver, DLQ Retrier, Heartbeat). Specs are in `docs/workflows.md`. JSON waits for a passing import on the pinned image.
- Proven worker execution. Docker was not available on the Windows workspace that last updated this file.
- Grafana and Prometheus (P04 overlay).

## One-time local n8n owner setup

After `make up`:

1. Open http://127.0.0.1:5678
2. Create the owner account in the setup screen. Local only.
3. Create an API key in n8n settings and put it in `.env` as `N8N_API_KEY`.
4. Never commit `.env` or the key.

TODO(verify): exact menu names on n8n 2.37.9.

## Tests

```bash
python scripts/run_unit_tests.py
python -m pytest -q platform/tests/e2e
```

Platform e2e skips when n8n and flaky-api are not reachable, or when `platform/workflows/` has no JSON.
