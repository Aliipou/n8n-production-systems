# n8n Production Systems

I design and operate production automation systems with n8n. n8n orchestrates; tested services do the computing.

This is a personal portfolio (reference implementations, synthetic data). It is not client work and not a production deployment.

Owner: [Ali Pourrahim](https://github.com/Aliipou). Helsinki.

Pinned n8n: Community Edition `n8nio/n8n:2.37.9` in queue mode (Postgres, Redis, one main, two workers). Pins: [platform/VERSIONS.md](platform/VERSIONS.md).

## What this repo shows

Employers and clients can inspect, clone, and run the same systems. Each project is built to fail in a documented way: duplicates, timeouts, 429s, 500s, worker kills, and prompt injection.

| Ability | Where it lives |
|---|---|
| Real integrations behind webhooks | P01 CRM sync (mock until a HubSpot test-mode run), P03 signed ingress |
| Idempotency, retries, dead-letter recovery | Platform `ops` schema, planned `[PLT] Error Handler` and `[PLT] DLQ Retrier` |
| Self-hosted n8n in queue mode | [platform/compose/docker-compose.base.yml](platform/compose/docker-compose.base.yml) |
| LLM with human approval and validators | P01 scoring cap 20/100, P02 evidence-checked extraction (validators in code) |
| Webhook signatures and credentials | P03 raw-body HMAC; secrets never in node output |
| Measured results, not slogans | Each project's `docs/results.md` after the measurement script runs |

Numbers in READMEs come from scripts in this repo. Until a script has been run, the value is "not measured yet".

No n8n workflow JSON is committed yet. Workflows are specified in each `docs/workflows.md` and must be built in the pinned local n8n, imported, published, and e2e-tested before export (see [AGENTS.md](AGENTS.md) section 5). This machine does not have Docker, so that gate has not been run here.

## Projects

| ID | Project | Stack | Status | Demo |
|---|---|---|---|---|
| [Platform](platform/README.md) | Shared n8n queue stack, mocks, error taxonomy, CI | n8n 2.37.9 CE, Postgres 16, Redis 7.4, FastAPI, Go | in progress (compose and unit tests in repo; stack not started on this laptop) | not recorded yet |
| [P01](projects/p01-lead-qualification) | Lead qualification and sales follow-up | n8n, FastAPI, Postgres | in progress (normalize/score backend and unit tests; no workflow JSON) | not recorded yet |
| [P02](projects/p02-document-intelligence) | Invoice extraction with human review | n8n, FastAPI, Tesseract (later) | in progress (upload, sha256 dedupe, validators; OCR/LLM later) | not recorded yet |
| [P03](projects/p03-webhook-gateway) | Signed webhook inbox and idempotent handlers | Go, n8n, Postgres | in progress (ingress + HMAC unit tests; dispatcher and workflows later) | not recorded yet |
| [P04](projects/p04-reliability) | Dashboards, alerts, chaos reports | Prometheus, Grafana, Alertmanager | skeleton (compose and provisioning; no measured chaos) | not recorded yet |
| [P05](projects/p05-multi-tenant) | Tenant-aware lead flow (reference architecture) | FastAPI, Go, Postgres RLS | skeleton (schema, RLS SQL, fictional tenant YAML; no gateway) | not recorded yet |

None of these is a v1.0.0 release. Definition of Done is in [docs/PLAN.md](docs/PLAN.md) section 7. n8n workflows, `make demo`, and recorded videos are still open.

### P01 Lead qualification

Inbound form leads are validated, deduplicated, scored with a documented rules engine, and synced to a mock CRM (HubSpot only after a real test-mode run). The LLM classifies intent and is capped at 20 of 100 score points. AI-drafted first emails wait for human approval. Follow-ups stop on reply, booking, bounce, or unsubscribe.

### P02 Invoice processing

Text and scanned invoices (Finnish and English) are extracted with evidence: every value must quote source text or it is rejected. Deterministic checks cover totals, VAT, Finnish business IDs, IBANs, and duplicates. An IBAN that does not match the supplier registry always goes to a reviewer.

### P03 Webhook gateway

A Go ingress verifies provider signatures on the raw body and stores the event before it returns 2xx. Delivery to n8n is at-least-once. Handlers are idempotent. The headline demo is: send events while n8n is down, start n8n, show zero lost events and zero duplicate side effects. That run is not measured yet.

### P04 Monitoring

Prometheus, Grafana, and Alertmanager watch the stack. Chaos scenarios in `projects/p04-reliability/chaos/` are named only. No recovery times are published until a script in this repo is actually run.

### P05 Multi-tenant (reference architecture)

One shared n8n instance with per-tenant config, API keys, and Postgres row-level security. n8n does not hold tenant secrets. This is not a hosted product. Read the n8n licence before thinking about hosted use: https://docs.n8n.io/sustainable-use-license/

## Run locally

Needs Docker, Docker Compose, GNU Make, and a copy of `.env.example` as `.env` with placeholder secrets replaced. Bind addresses stay on `127.0.0.1`.

```bash
git clone https://github.com/Aliipou/n8n-production-systems
cd n8n-production-systems
cp .env.example .env
make up
make up P=p01
```

Short `P=` values: `p01`, `p02`, `p03`, `p04`, `p05` (or the full folder name).

URLs after a successful `make up`:

- n8n editor: http://127.0.0.1:5678
- Mailpit: http://127.0.0.1:8025
- mock-llm: http://127.0.0.1:8090
- flaky-api: http://127.0.0.1:8091
- review-ui: http://127.0.0.1:8092
- P01 backend: http://127.0.0.1:8101
- P02 doc-service: http://127.0.0.1:8102
- P03 ingress: http://127.0.0.1:8103
- Grafana (with P04 overlay): http://127.0.0.1:3000

One-time n8n owner setup is in [platform/README.md](platform/README.md). Never commit `.env`.

Unit tests without Docker:

```bash
python scripts/run_unit_tests.py
```

On GNU Make: `make test` and `make check`. Platform e2e (`make e2e`) skips unless n8n, flaky-api, and committed workflow JSON are present.

## Repository map

```text
platform/     compose, ops migrations, mocks, review-ui, workflow specs
projects/     p01 to p05: backends, SQL, workflow specs, docs
code-snippets/  JavaScript used in Code nodes, with Vitest
scripts/      import, export, sanitize, lint, unit-test runner
docs/         plan, specs, ADRs, progress, questions
AGENTS.md     rules for anyone (or any agent) committing here
```

## Limits

- Community Edition only. No n8n Enterprise features.
- Fixtures are synthetic. No real people, invoices, or customer records.
- Provider names (HubSpot, Stripe, Shopify) appear as "tested against the real API" only after a real test-mode call, not only a mock.
- P05 is not a product you can sell hosted access to.
- Docker was not installed on the Windows workspace that wrote this status. Worker execution and n8n import are unproven here.
- No latency, accuracy, or cost figure is published yet.

## License

MIT for code in this repository. n8n is not included and is licensed separately by n8n GmbH. See `NOTICE`.
