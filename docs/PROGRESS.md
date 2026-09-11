# Progress

| Date | Task ID | What changed | Known gaps | Commit |
|---|---|---|---|---|
| 2026-09-11 | PLT-T01 | Repo skeleton: layout, gitignore, editorconfig, env example, pre-commit, LICENSE, NOTICE, Makefile stubs, PR template, platform README | Stack not running. Workflow sanitize/lint hooks point at scripts that do not exist yet (PLT-T07). make check is a stub. | fb50edf |
| 2026-09-11 | PLT-T01 | Portfolio README index with honest status labels and no invented numbers | GitHub create/push depends on a valid `gh` token. Compose still missing (PLT-T03). | |
| 2026-09-11 | PLT-T02 | Version pins in progress (`platform/VERSIONS.md` started). | Image digests and some n8n env names still TODO(verify). Owner has not confirmed 2.x pin. | |
| 2026-09-11 | PLT-T03 | Base compose in progress (queue mode, workers, 127.0.0.1 binds). | Docker not installed on this Windows workspace. Worker execution not proven. | |
| 2026-09-11 | PLT-T04 | `ops` migrations and grant tests in progress. | Needs a running Postgres. Grant UPDATE-deny test skipped without DATABASE_URL. | |
| 2026-09-11 | PLT-T05 | mock-llm FastAPI in progress. | Compose image build untested here. | |
| 2026-09-11 | PLT-T06 | flaky-api Go service in progress. | Go may be missing locally. Race tests run in CI when go.mod is present. | |
| 2026-09-11 | PLT-T07 | sanitize/lint/import/export scripts in progress. | CLI flags TODO(verify) on the pinned n8n. No committed workflow JSON yet. | |
| 2026-09-11 | PLT-T08 | Error taxonomy JS and Python plus shared fixtures in progress. | Cross-language fixture test must stay in CI. | |
| 2026-09-11 | PLT-T09 | `[PLT] Error Handler` and `[PLT] Notify` not built in n8n yet. | Needs running pinned n8n. JSON cannot be committed until import and e2e pass. | |
| 2026-09-11 | PLT-T10 | review-ui skeleton in progress. | HMAC e2e against n8n not run. | |
| 2026-09-11 | PLT-T11 | `[PLT] DLQ Retrier` and `[PLT] Heartbeat` not built in n8n yet. | Same workflow lifecycle gate as T09. | |
| 2026-09-11 | PLT-T12 | `.github/workflows/ci.yml` and `security.yml`; `docs/branch-protection.md`. Jobs named `lint`, `unit`, `secrets`, `e2e`. Actions pinned to full tags or SHA. e2e uses compose on `platform/`, `scripts/`, `code-snippets/` path filters. | Pipeline not observed green on GitHub. Compose `--wait` untested here (no Docker). No platform e2e tests yet (PLT-T13). Owner must apply branch protection. | |
| 2026-09-11 | PLT-T13 | Platform e2e not implemented. | Needs compose, imported workflows, Mailpit, flaky-api 500 then heal, DLQ retry, exactly one success. | |
| 2026-09-11 | PLT-T14 | ADRs `0001` to `0005`; PROGRESS and QUESTIONS updated. README index already from T01. | Owner-answer column in QUESTIONS.md is still empty. Branch protection is a doc, not a GitHub setting. | |
| 2026-09-11 | PLT-T09 | Specs for `[PLT] Error Handler` and `[PLT] Notify` in `platform/docs/workflows.md`. | No JSON until pinned n8n import and e2e. Docker missing on this laptop. | |
| 2026-09-11 | PLT-T11 | Specs for `[PLT] DLQ Retrier`, `[PLT] Heartbeat`, and `[PLT] Flaky Probe` in the same file. | Same JSON gate as T09. | |
| 2026-09-11 | PLT-T13 | `platform/tests/e2e` added. Tests skip without stack or workflow JSON. | The 500-heal-one-success path is not proven. | |
| 2026-09-11 | PLT-T14 | Root README lists all phases with honest in-progress/skeleton status. P01 README follows the project template. Makefile `test`/`check`/`e2e` call real scripts. `P=p01`..`p05` map to folder names. P05 migrate overlay added. | DoD not met: no Docker run, no workflow JSON, no demos, no measured results. | |
