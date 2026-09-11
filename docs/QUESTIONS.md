# Open questions

| Date | Task ID | Question | Options seen | Answer (owner) |
|---|---|---|---|---|
| 2026-09-11 | PLT-T01 | Root `PLAN.md` duplicates `docs/PLAN.md`. Root copy is gitignored. Delete the root file? | Keep untracked; delete; stop ignoring and track both | |
| 2026-09-11 | PLT-T01 | This machine has no Docker, GNU Make, or Go. Python is 3.13.2 (spec asks 3.12). Node is v24.5.0. How should local Phase 0 run on Windows? | WSL2 with Ubuntu; Git Bash plus Make; install Docker Desktop, Make, Go, and Python 3.12 on Windows | |
| 2026-09-11 | PLT-T02 | Which n8n 2.x image to pin? GitHub `latest` redirect on 2026-09-11 was `n8n@2.38.7`. Archived 2.x notes still listed stable `2.37.9` and beta `2.38.3`. Docker Hub listings also showed `2.39.1`. | Pin the GitHub stable channel after reading current docs.n8n.io; pin `2.38.7`; wait for owner pick | |
| 2026-09-11 | PLT-T02 | Postgres 16 or 17 for the official Docker image? | 16; 17 | |
| 2026-09-11 | PLT-T01 | `gh` reports invalid keyring token (HTTP 401). Repo create and push are blocked until `gh auth login`. The PAT pasted in chat will not be used. | Owner re-authenticates; owner creates the empty GitHub repo and we add the SSH remote | Repo exists. Work is on `main`. Owner will revoke chat PATs and run `gh auth login`. |
| 2026-09-11 | PLT-T03 | Docker Desktop is not installed on this Windows 10 workspace, so `make up`, worker proof, T09/T11 JSON, and T13 cannot finish here. | Install Docker Desktop; WSL2 Ubuntu; skip local stack and rely on GitHub Actions e2e | |
| 2026-09-11 | PLT-T01 | pre-commit gitleaks rev is `v8.30.0` because `v8.30.1` is an orphan tag that breaks `pre-commit autoupdate` (gitleaks issue 2086). Switch when `v8.30.2` exists? | Stay on `v8.30.0`; bump later | |
| 2026-09-11 | PLT-T02 | NOTICE links https://docs.n8n.io/sustainable-use-license/ . Confirm that URL for the pinned n8n version. | Keep; replace with the URL n8n publishes at pin time | |
| 2026-09-11 | PLT-T12 | `pip-audit` has no `--severity` filter and fails on any finding. Fail-all is stricter than high/critical. Keep fail-all, or filter JSON later? | Fail-all; JSON plus jq for HIGH/CRITICAL; document exceptions in `docs/security-exceptions.md` | |
| 2026-09-11 | PLT-T12 | `govulncheck` fails on reachable vulns, not CVSS high. Same policy question as pip-audit. | Keep reachable-vuln fail; add a high-only filter if a pin supports it | |
| 2026-09-11 | PLT-T12 | Trivy Action tags were force-pushed in a 2026-03 supply-chain incident. CI pins `aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25` (v0.36.0) and Trivy `v0.70.0`. Confirm this SHA before relying on it. | Keep SHA; move to a later signed release the owner names | |
| 2026-09-11 | PLT-T12 | Should `security` be a required check on `main`? The workflow skips on PRs that do not touch dependency files, which blocks merge if the check is required. | Required only after a no-op job always runs; leave it optional and read the weekly run | |
| 2026-09-11 | PLT-T12 | pytest `--cov-fail-under=85` runs when any `src/` directory exists. Incomplete packages may fail the unit job before DoD. Keep 85% now, or wait until each backend opts in via pyproject? | Keep 85% now; per-package fail-under; report coverage without failing until P01 DoD | |
| 2026-09-11 | PLT-T12 | CI uses Node `22.23.2` (maintenance LTS). This machine has Node v24.5.0. Active LTS in 2026 is 24.x. Which line for `code-snippets`? | Stay on 22.23.2; pin 24.20.0; follow whatever `platform/VERSIONS.md` says | |
| 2026-09-11 | PLT-T14 | Required approving reviews on `main`: 0 (solo owner merges after checks) or 1? | 0 until a second reviewer exists; 1 from the start | |
