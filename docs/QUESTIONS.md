# Open questions

| Date | Task ID | Question | Options seen | Answer (owner) |
|---|---|---|---|---|
| 2026-09-11 | PLT-T01 | Root `PLAN.md` duplicates `docs/PLAN.md`. Root copy is gitignored. Delete the root file? | Keep untracked; delete; stop ignoring and track both | |
| 2026-09-11 | PLT-T01 | This machine has no Docker, GNU Make, or Go. Python is 3.13.2 (spec asks 3.12). Node is v24.5.0. How should local Phase 0 run on Windows? | WSL2 with Ubuntu; Git Bash plus Make; install Docker Desktop, Make, Go, and Python 3.12 on Windows | |
| 2026-09-11 | PLT-T02 | Which n8n 2.x image to pin? GitHub `latest` redirect on 2026-09-11 was `n8n@2.38.7`. Archived 2.x notes still listed stable `2.37.9` and beta `2.38.3`. Docker Hub listings also showed `2.39.1`. | Pin the GitHub stable channel after reading current docs.n8n.io; pin `2.38.7`; wait for owner pick | |
| 2026-09-11 | PLT-T02 | Postgres 16 or 17 for the official Docker image? | 16; 17 | |
| 2026-09-11 | PLT-T01 | `gh` reports invalid keyring token (HTTP 401). Repo create and push are blocked until `gh auth login`. The PAT pasted in chat will not be used. | Owner re-authenticates; owner creates the empty GitHub repo and we add the SSH remote | |
| 2026-09-11 | PLT-T01 | pre-commit gitleaks rev is `v8.30.0` because `v8.30.1` is an orphan tag that breaks `pre-commit autoupdate` (gitleaks issue 2086). Switch when `v8.30.2` exists? | Stay on `v8.30.0`; bump later | |
| 2026-09-11 | PLT-T02 | NOTICE links https://docs.n8n.io/sustainable-use-license/ . Confirm that URL for the pinned n8n version. | Keep; replace with the URL n8n publishes at pin time | |
