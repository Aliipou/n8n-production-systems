# n8n Production Systems

I design and operate production automation systems with n8n. n8n orchestrates; tested services do the computing.

This is a personal portfolio (reference implementations, synthetic data). It is not client work and not a production deployment.

Owner: [Ali Pourrahim](https://github.com/Aliipou). Helsinki.

## What this repo shows

Employers and clients can inspect, clone, and run the same systems. Each project is built to fail in a documented way: duplicates, timeouts, 429s, 500s, worker kills, and prompt injection.

| Ability | Where it lives |
|---|---|
| Real integrations behind webhooks | P01 CRM sync, P03 signed ingress |
| Idempotency, retries, dead-letter recovery | Platform `ops` schema, `[PLT] Error Handler`, `[PLT] DLQ Retrier` |
| Self-hosted n8n in queue mode | Phase 0: Postgres, Redis, main plus two workers |
| LLM with human approval and validators | P01 email drafts, P02 evidence-checked extraction |
| Webhook signatures and credentials | P03 raw-body HMAC, secrets never in node output |
| Measured results, not slogans | Each project's `docs/results.md` after the measurement script runs |

Numbers in READMEs come from scripts in this repo. Until a script has been run, the value is "not measured yet".

## Projects

| ID | Project | Stack | Status | Demo |
|---|---|---|---|---|
| Platform | Shared n8n queue stack, mocks, error taxonomy, CI | n8n 2.x Community Edition, Postgres, Redis, FastAPI, Go | in progress (Phase 0) | not recorded yet |
| [P01](projects/p01-lead-qualification) | Lead qualification and sales follow-up | n8n, FastAPI, Postgres | not started | not recorded yet |
| [P02](projects/p02-document-intelligence) | Invoice extraction with human review | n8n, FastAPI, Tesseract | not started | not recorded yet |
| [P03](projects/p03-webhook-gateway) | Signed webhook inbox and idempotent handlers | Go, n8n, Postgres | not started | not recorded yet |
| [P04](projects/p04-reliability) | Dashboards, alerts, chaos reports | Prometheus, Grafana, Alertmanager | not started (after P01 to P03) | not recorded yet |
| [P05](projects/p05-multi-tenant) | Tenant-aware lead flow (reference architecture) | FastAPI, Go, Postgres RLS | not started (after P01 to P03) | not recorded yet |

Order is fixed. A project is not started until the previous one meets the [Definition of Done](docs/PLAN.md#7-definition-of-done-every-project).

### P01 Lead qualification

Inbound form leads are validated, deduplicated, scored with a documented rules engine, and synced to a mock CRM (HubSpot only after a real test-mode run). The LLM classifies intent and is capped at 20 of 100 score points. AI-drafted first emails wait for human approval. Follow-ups stop on reply, booking, bounce, or unsubscribe.

### P02 Invoice processing

Text and scanned invoices (Finnish and English) are extracted with evidence: every value must quote source text or it is rejected. Deterministic checks cover totals, VAT, Finnish business IDs, IBANs, and duplicates. An IBAN that does not match the supplier registry always goes to a reviewer.

### P03 Webhook gateway

A Go ingress verifies provider signatures on the raw body and stores the event before it returns 2xx. Delivery to n8n is at-least-once. Handlers are idempotent. The headline demo is: send events while n8n is down, start n8n, show zero lost events and zero duplicate side effects. That run is not measured yet.

### P04 and P05

P04 adds metrics, alerts, a dead man's switch, circuit breakers, and recorded chaos. P05 reuses the lead flow with per-tenant config, row-level security, and credentials kept out of n8n execution data. P05 is a reference architecture; read the n8n licence before thinking about hosted use.

## Run locally

Phase 0 compose is not in the repo yet (`PLT-T03`). After `make up` exists:

```bash
git clone https://github.com/Aliipou/n8n-production-systems
cd n8n-production-systems
cp .env.example .env
make up P=p01
make demo P=p01
```

Copy `.env.example` only. Never commit `.env`. Bind addresses stay on `127.0.0.1`. One-time n8n owner setup is in `platform/README.md`.

## Repository map

```text
platform/     shared stack, ops schema, mocks, platform workflows
projects/     p01 to p05, each with backend, workflows, tests, docs
scripts/      import, export, sanitize, lint (from PLT-T07)
docs/         plan, specs, ADRs, progress
AGENTS.md     rules for anyone (or any agent) committing here
```

## Limits

- Community Edition only. No n8n Enterprise features.
- Fixtures are synthetic. No real people, invoices, or customer records.
- Provider names (HubSpot, Stripe, Shopify) appear in resume and README only after a real test-mode API call, not only a mock.
- P05 is not a product you can sell hosted access to.

## License

MIT for code in this repository. n8n is not included and is licensed separately by n8n GmbH. See `NOTICE`.
