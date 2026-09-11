# ADR 0001: One monorepo

Date: 2026-09-11
Status: Accepted

## Context

The portfolio is several automation systems that share a queue-mode n8n stack, an `ops` schema, mock services, error handling, a review UI, workflow sanitize/lint scripts, and CI. The GitHub profile has a limited number of pinned repositories. Clients and hiring readers should get one URL with deep links into project folders.

## Decision

Keep all platform code and projects P01 to P05 in one repository named `n8n-production-systems`. Shared code lives under `platform/`, `scripts/`, and `code-snippets/`. Each project lives under `projects/p0N-*/`. One CI workflow with path filters covers the tree.

## Alternatives

1. Five separate repositories, one per project, plus a platform repo. More search surface on GitHub. Platform code would be copied or published as a package. Five CI setups and five version pins to keep in sync.
2. A platform repo plus project repos that vendor a release of the platform. Clearer release boundaries. Extra release work before any project can move.

Rejected for now: five separate repositories. Revisit only if one piece needs its own releases. The workflow linter is the most likely candidate to extract later.

## Consequences

- Platform changes land once and are reused. Duplicate compose files and error handlers are avoided.
- CI, branch protection, and `make check` are defined once.
- The profile pin is one repository. Project READMEs must link clearly so a reader can jump to P01 without opening the whole tree.
- A broken platform change can affect every project. Path filters and project e2e jobs limit how much runs, they do not isolate release cadence.
- Git history and issue tracker are shared. Commit scopes (`feat(p01)`, `feat(platform)`) must stay specific.
