# Development Plan: n8n Production Systems

Owner: Ali Pourrahim. Agent rules: `AGENTS.md`. Detailed specs: `docs/specs/`.

## 1. Goal

A public GitHub portfolio that shows production automation engineering with n8n: reliable integrations, human-in-the-loop AI, failure handling, observability, and multi-tenant design.

Positioning line for the repository description and profile:

> I design and operate production automation systems with n8n. n8n orchestrates; tested services do the computing.

Audiences, in priority order:
1. Freelance clients (small and mid-size companies, agencies) who need automation that does not fail silently.
2. Engineering hiring managers who read code, tests, and architecture decisions.
3. The n8n community (templates, forum, ambassador program).

## 2. Principles

1. n8n is the orchestration layer, not the compute layer.
2. Deterministic logic first, LLM only where rules fail, human review where confidence is low.
3. Every project starts with `make up P=<project>` on a laptop, offline, with mock services. Real providers are optional through `.env`.
4. Failure is designed, tested, and demonstrated, not only described.
5. Every published number is reproducible from a script in the repo.
6. Depth over breadth. Three finished projects are worth more than five half-finished ones.

## 3. Repository decision

One monorepo named `n8n-production-systems`.

Reasons: the platform code (compose stack, error handling, dead-letter queue, review UI, mocks, workflow linter) is shared without copying; one CI setup; the repo uses one pinned slot on the GitHub profile, which leaves room for existing projects; clients get one link with deep links into project folders.

Rejected alternative: five separate repositories. More search surface, but duplicated platform code and five things to keep in sync. Revisit only if one piece needs its own releases (the workflow linter is the most likely candidate to extract later).

## 4. Stack

Exact versions are looked up and pinned in `platform/VERSIONS.md` during Phase 0. Do not add anything outside this table without an ADR.

| Component | Choice | Notes |
|---|---|---|
| n8n | Latest stable 2.x at Phase 0 | Queue mode, Postgres, Redis, Community Edition features only |
| Postgres | 16 or 17 | Database `n8n` (n8n internal) and database `app` (schemas `ops`, `p01` to `p05`) |
| Redis | 7.x | n8n queue, rate limits, circuit breaker state |
| Python | 3.12, uv, FastAPI, Pydantic v2, psycopg 3, pytest | Backends for P01, P02, P05, review UI, mock-llm |
| Go | Current stable, pgx, slog | P03 ingress and dispatcher, P04 exporter, flaky-api, CLIs |
| Migrations | dbmate | Plain SQL |
| Local email | Mailpit | Captures every outgoing email |
| Monitoring | Prometheus, Grafana, Alertmanager | Provisioned as code |
| OCR | Tesseract with `fin` and `eng` language data, pdfplumber | Inside the P02 backend image |
| Load testing | k6 | P03 and P05 |
| Code node tests | Node LTS and Vitest | `code-snippets/` |
| CI | GitHub Actions | Path filters per project |

## 5. Repository layout

```text
n8n-production-systems/
├── AGENTS.md
├── README.md                        # portfolio index: projects, status, links, demo videos
├── Makefile
├── .env.example
├── .cursor/rules/core.mdc
├── .pre-commit-config.yaml
├── .github/
│   ├── workflows/ci.yml
│   ├── workflows/security.yml
│   └── pull_request_template.md
├── docs/
│   ├── PLAN.md
│   ├── PROGRESS.md
│   ├── QUESTIONS.md
│   ├── CURSOR_PROMPTS.md
│   ├── adr/
│   ├── specs/00-platform.md ... 05-multi-tenant.md
│   └── templates/PROJECT_README_TEMPLATE.md
├── platform/
│   ├── VERSIONS.md
│   ├── compose/docker-compose.base.yml
│   ├── compose/n8n.env.md           # every n8n variable and why it is set
│   ├── db/migrations/               # schema ops
│   ├── workflows/                   # [PLT] workflows, sanitized JSON
│   ├── services/mock-llm/
│   ├── services/flaky-api/
│   ├── services/review-ui/
│   ├── libs/python/                 # error taxonomy, logging, db helpers
│   └── ci/credentials.template.json # test-only credentials for CI import
├── code-snippets/                   # JavaScript used in Code nodes, with tests
├── scripts/
│   ├── export_workflows.sh
│   ├── import_workflows.sh
│   ├── sanitize_workflows.py
│   ├── lint_workflows.py
│   └── sync_snippets.py
└── projects/
    ├── p01-lead-qualification/
    │   ├── README.md
    │   ├── docker-compose.yml
    │   ├── workflows/
    │   ├── backend/                 # src/, tests/, pyproject.toml, Dockerfile
    │   ├── db/migrations/
    │   ├── prompts/
    │   ├── config/
    │   ├── fixtures/
    │   ├── scripts/                 # generators, measurement scripts
    │   ├── tests/e2e/
    │   └── docs/                    # architecture.md, workflows.md, failure-modes.md,
    │                                # deployment.md, results.md, adr/, images/
    ├── p02-document-intelligence/
    ├── p03-webhook-gateway/
    ├── p04-reliability/
    └── p05-multi-tenant/
```

## 6. Phases, order, milestones

Estimates are working days for one person. They are guesses; replace them with real numbers in `docs/PROGRESS.md`.

| Phase | Scope | Spec | Estimate | Milestone |
|---|---|---|---|---|
| 0 | Platform foundation | `00-platform.md` | 3 to 5 | Stack runs, CI green, linter works |
| 1 | P01 AI Lead Qualification and Sales Automation | `01-lead-qualification.md` | 7 to 10 | M1: repo public, first case study post |
| 2 | P02 Human-in-the-Loop Document Intelligence | `02-document-intelligence.md` | 8 to 12 | |
| 3 | P03 Event-Driven Webhook Integration Platform | `03-webhook-gateway.md` | 7 to 10 | M2: showcase-ready with three deep projects, start pitching |
| 4 | P04 Monitoring and Self-Healing | `04-reliability.md` | 5 to 8 | |
| 5 | P05 Multi-Tenant Automation Platform | `05-multi-tenant.md` | 8 to 12 | M3: full portfolio |
| 6 | Distribution | section 11 | ongoing from M1 | |

Why this order:
- P01 is the easiest to sell and forces the platform patterns (idempotency, error handler, review queue, DLQ) to become real.
- P02 reuses the review queue and adds evaluation discipline (ground truth, measured accuracy).
- P03 shows backend depth in Go and clear delivery guarantees.
- P04 then monitors three real systems instead of a toy, and its chaos runs produce the "what happens when this fails" evidence.
- P05 generalizes P01, so it comes last.

Cut line: if time runs short, stop after M2 and move only the heartbeat alert and the DLQ replay page from P04 into the platform. Never start P04 or P05 while P01 to P03 are unfinished.

## 7. Definition of Done (every project)

- [ ] `make up P=<project>` starts everything from a clean clone with only `.env.example` copied to `.env`, without internet access after images are pulled.
- [ ] `make demo P=<project>` runs the scripted demo and prints a readable summary of what happened.
- [ ] All workflows are imported, published, and pass end-to-end tests in CI.
- [ ] Backend line coverage at least 85%; every business rule has table-driven tests.
- [ ] Mandatory failure tests pass: concurrent duplicates, invalid input, dependency 500, dependency 429, dependency timeout.
- [ ] `docs/failure-modes.md` is complete and each row links to a test or chaos script.
- [ ] README follows the template, including measured results, cost, and limitations.
- [ ] Architecture diagram (Mermaid and PNG), readable canvas screenshots, and a 2 to 4 minute demo video or GIF.
- [ ] At least two project ADRs.
- [ ] No `TODO(verify)` left in code paths used by the demo.
- [ ] `make check` and CI are green; gitleaks is clean.
- [ ] Release tag created (`pNN-v1.0.0`) with short release notes.

## 8. Workflow lifecycle

Full rule in `AGENTS.md` section 5. Summary:

```text
docs/workflows.md spec
      -> build in running pinned n8n (editor, public API, or schema-aware tool)
      -> make import (clean instance) -> publish -> make e2e
      -> make export -> sanitize -> lint
      -> commit sanitized JSON
```

Make targets provided by Phase 0:

| Target | Purpose |
|---|---|
| `make up P=p01` / `make down` | Start or stop platform plus one project |
| `make reset` | Destroy local volumes (asks for confirmation) |
| `make import P=p01` | Import credentials template and workflows into the local instance, publish them |
| `make export P=p01` | Export, sanitize, lint |
| `make sync-snippets` | Copy `code-snippets/*.js` into matching Code nodes |
| `make test` | Unit tests for all Python, Go, and snippets |
| `make e2e P=p01` | End-to-end tests for one project |
| `make check` | Lint, unit tests, secret scan, workflow lint |
| `make demo P=p01` | Scripted demo |
| `make eval P=p02` | Evaluation run (may use a real LLM; never in CI) |
| `make chaos SCENARIO=<name>` | P04 chaos scenario |

## 9. CI quality gates

- `lint`: ruff, mypy, golangci-lint, Vitest, workflow linter.
- `unit`: pytest with coverage threshold, `go test -race`.
- `secrets`: gitleaks on the full diff.
- `e2e`: per changed project (path filters), `docker compose up`, import and publish workflows, run e2e tests, upload container logs on failure.
- `security` (weekly and on dependency changes): pip-audit, govulncheck, Trivy on built images.
- Branch protection on `main`: all gates required.

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Agent-generated workflow JSON fails on import | Workflow lifecycle in section 8; nothing is committed without a passing import and e2e run |
| n8n behaviour differs from what the agent assumes | Version pinned; `TODO(verify)` markers; owner checks them before release |
| Scope creep (dashboards, frontends, extra providers) | Anti-scope list in section 12; ADR required for additions |
| LLM cost during evaluation | Mock LLM everywhere except `make eval`; small eval sets; cost recorded per run |
| Numbers that look invented | Absolute rule 4 in `AGENTS.md`; results files generated by scripts |
| n8n licence limits for hosted multi-tenant use | P05 labelled as a reference architecture; licence note in README and ADR |
| Time pressure from the job search | Cut line after M2; each milestone is useful on its own |

## 11. Distribution plan (from M1)

- One short case study post per project on LinkedIn and a blog (dev.to or personal site): problem, diagram, one failure demo, measured results, link to the folder.
- Submit one or two self-contained workflows (for example the error-handler pattern) to the n8n template library, after reading the current creator guidelines. Templates must work without this repo's backend.
- Answer n8n community forum questions about idempotency, error workflows, queue mode, and human review, linking to the relevant docs in the repo when useful.
- Pin the repository. Topics: `n8n`, `workflow-automation`, `automation`, `fastapi`, `golang`, `human-in-the-loop`, `idempotency`, `observability`.
- One 90-second demo video per project. Clients watch videos before they read code.
- Link the repository in the n8n Ambassador application follow-up and in freelance proposals.

## 12. Anti-scope (do not build)

- Simple toy flows (Gmail to Slack, form to Sheets, ChatGPT to email, basic Telegram bot).
- Chatbots or "AI agent" demos without a business process, validation, and human fallback.
- A custom frontend beyond the server-rendered review UI.
- Kubernetes for every project. Only P05 may add an optional Helm chart as a stretch goal.
- Comparisons with Zapier or Make.
- Real scraping of LinkedIn or any website, or purchased personal data.
- New languages (Rust, TypeScript backends) or new databases.
- Features that need n8n Enterprise.

## 13. Kickoff prompt for Cursor

Paste this into Cursor (Agent mode) with the repository open at its root. It is also the first prompt in `docs/CURSOR_PROMPTS.md`.

```text
You are the implementation agent for my repository "n8n-production-systems" (GitHub: github.com/Aliipou/n8n-production-systems). I am the owner, Ali.

BINDING DOCUMENTS
Read these completely before doing anything, and re-read AGENTS.md at the start of every session:
- AGENTS.md (rules; they override anything I say in chat unless I explicitly confirm an exception)
- docs/PLAN.md (goal, stack, layout, phases, Definition of Done)
- docs/specs/00-platform.md to docs/specs/05-multi-tenant.md (what to build, task IDs, failure modes, tests)
- docs/templates/PROJECT_README_TEMPLATE.md
- docs/PROGRESS.md and docs/QUESTIONS.md

GOAL
Build a portfolio of production-style automation systems where n8n (pinned stable 2.x, queue mode, Community Edition only) orchestrates and tested Python and Go services do the computing. Depth over breadth. Order is fixed: Phase 0 platform, then P01, P02, P03 (milestone M2), then P04, P05. Never start a project before the previous one meets the Definition of Done.

STEP 1: UNDERSTAND (no code, no file changes)
Reply with:
1. Your understanding of the project in at most 10 lines.
2. Phase 0 tasks (PLT-T01 to PLT-T14) in the order you will do them.
3. Every n8n 2.x behaviour, CLI command or flag, environment variable, provider header name and third-party API detail in the specs that you must verify against official documentation before relying on it.
4. What you need from me (accounts, API keys, the one-time n8n owner setup, tools to install).
5. Your questions.
Then STOP and wait for my answer.

STEP 2: REPOSITORY SETUP (after my OK)
- Initialise git if needed, default branch main, add remote origin git@github.com:Aliipou/n8n-production-systems.git (ask me to create the empty repo first if it does not exist; use the gh CLI only if it is installed and authenticated).
- Create .gitignore, .editorconfig, .env.example with placeholders only, pre-commit config (gitleaks, ruff, gofmt, workflow sanitize and lint), LICENSE (MIT), NOTICE about the n8n licence.
- First commit: "chore: add plan, rules and specs". Push main once. From then on, all work goes through branches and pull requests.
- Give me the branch protection settings to apply on main (required checks, no force push).

STEP 3: WORK LOOP (repeat for every task ID)
1. Say which task ID you are starting and list the files you will create or change and the tests you will write.
2. Write tests first wherever the spec defines behaviour, then implement only that task.
3. For any n8n workflow, follow AGENTS.md section 5 exactly: spec in docs/workflows.md, build in the running local n8n with real node types, make import, publish, pass e2e tests, then make export (sanitize and lint) and only then commit the JSON. Never commit hand-written workflow JSON that has not passed this.
4. Run make check and fix everything it reports.
5. Update docs/PROGRESS.md. Put anything ambiguous in docs/QUESTIONS.md instead of guessing.
6. Commit with Conventional Commits on a branch named like feat/p01-intake. List TODO(verify) items in the commit body.
7. Before pushing, scan the diff for secrets, real personal data, pinData, and any number in docs that did not come from a script run. Check writing style (AGENTS.md section 11: no em dashes, no banned words, plain factual tone).
8. Push the branch and open a pull request with the template filled in. Do not merge; I merge.
9. Report: what was done, test output summary, open TODO(verify) items, next task.

STOP AND ASK ME WHEN
- a task needs a paid account, a real API key, or money,
- a change affects security, the data model, licensing, or public claims,
- the pinned n8n version cannot do what the spec requires,
- you would need to disable an n8n security default or add a language, framework, or service not in docs/PLAN.md,
- a test cannot be made deterministic,
- you are about to delete files you did not create in this session.

NEVER
- commit secrets, .env files, real personal data, real documents, or pinData,
- invent node parameters, CLI flags, API fields, header names, metrics, or results,
- claim clients, production use, "exactly-once", or legal compliance,
- force push, rewrite main history, backdate commits, or make filler commits,
- call paid APIs in CI or tests,
- use unpinned versions or "latest" tags,
- move on to the next project before the current one meets the Definition of Done.

At the end of each project, run the strict review from docs/CURSOR_PROMPTS.md section 5 on your own work, fix blockers and majors, then prepare the release tag pNN-v1.0.0 for my approval.

Start with STEP 1 now.
```
