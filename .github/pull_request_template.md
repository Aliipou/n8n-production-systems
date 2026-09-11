## Task

- Task ID:
- Spec:

## Summary

<!-- What changed and why. Plain factual tone. No marketing words. -->

## Definition of Done

- [ ] `make up P=<project>` starts from a clean clone with `.env.example` copied to `.env` (when this PR touches runtime)
- [ ] Tests added or updated for the behaviour in the spec
- [ ] Mandatory failure tests still pass if this project has them: concurrent duplicates, invalid input, dependency 500, dependency 429, dependency timeout
- [ ] `make check` passes
- [ ] No secrets, `.env`, real personal data, or `pinData`
- [ ] No numbers in docs except those produced by a script in this repo (or "not measured yet")
- [ ] Workflow JSON (if any) was imported into the pinned local n8n, published, and passed e2e before commit
- [ ] `docs/PROGRESS.md` updated
- [ ] Ambiguities went to `docs/QUESTIONS.md` instead of guesses
- [ ] `TODO(verify)` items listed below

## TODO(verify)

<!-- What, why, which official doc to check. Write "none" if empty. -->

## Test plan

- [ ]
