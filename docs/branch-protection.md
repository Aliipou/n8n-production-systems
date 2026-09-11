# Branch protection for `main`

Apply this in GitHub: Settings, Branches, Add branch ruleset (or classic Branch protection) for `main`.

Required status check names must match the GitHub Actions **job names** in `.github/workflows/ci.yml` (the `name:` field on each job, which is also the job id).

## Required status checks

These four must pass before merge. They come from `.github/workflows/ci.yml`:

| Check name | Job | What it runs |
|---|---|---|
| `lint` | `lint` | ruff; mypy if `src/` Python exists; golangci-lint if `go.mod` exists; vitest if `code-snippets/package.json` exists; workflow linter if `scripts/lint_workflows.py` exists |
| `unit` | `unit` | pytest (coverage threshold 85% once `src/` exists); `go test -race` if `go.mod` exists |
| `secrets` | `secrets` | gitleaks `detect` on the full git history of the checkout |
| `e2e` | `e2e` | Always reports. Docker Compose and tests run only when the diff includes `platform/`, `scripts/`, or `code-snippets/` |

Do not require a check named `CI` (workflow name). Require the job names above.

## Security workflow

`.github/workflows/security.yml` job name: `security`.

It runs on a weekly cron, on `workflow_dispatch`, and on changes to dependency files or Dockerfiles. It is **not** a required check on every pull request. If you add `security` as required while it is skipped on unrelated PRs, GitHub leaves the check pending and merge stays blocked.

Add `security` as required only after that workflow runs on every PR (for example a no-op success step when no dependency files changed). Until then, still read the weekly run.

## Pull requests

- Require a pull request before merging into `main`. Do not allow direct pushes.
- Required approving reviews: 0 while this is a solo-owner repo (owner merges after checks). Set to 1 when a second reviewer exists.
- Require conversation resolution before merge.
- Do not allow bypassing the ruleset, except a documented break-glass admin path if GitHub forces one.

## Force push and deletion

- Do not allow force pushes to `main`.
- Do not allow deleting `main`.
- Do not allow force pushes on the branch ruleset for `main`.

`AGENTS.md` already forbids force push and history rewrite on `main`. This setting is the server-side copy of that rule.

## Other

- Require branches to be up to date before merge, once the four checks are stable. If that queues too many rebases while Phase 0 lands, turn it on after the first green week.
- Do not require signed commits unless the owner already signs every commit.
- Linear history is optional. Do not enable it until the owner wants rebase-only merges.

## After you save

1. Open a throwaway PR that only touches `docs/` and confirm `lint`, `unit`, `secrets`, and `e2e` all show on the PR (e2e should pass by skipping compose).
2. Open a PR that touches `platform/` and confirm e2e starts compose once `docker-compose.base.yml` exists.
3. Confirm Settings still lists the check names `lint`, `unit`, `secrets`, `e2e` exactly.
