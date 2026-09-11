# Pinned versions

Lookup date: 2026-09-11. Do not use `latest`, `next`, `stable`, or `beta` image tags in compose. Pin the versions in this file.

## Images used by `platform/compose/docker-compose.base.yml`

| Component | Pin | Image | Source (2026-09-11) |
|---|---|---|---|
| n8n Community Edition | 2.37.9 | `n8nio/n8n:2.37.9` | Official 2.x notes: current `stable` 2.37.9, current `beta` 2.38.3. https://docs.n8n.io/changelog/release-notes-2.x.md GitHub release `n8n@2.37.9` (2026-09-03). https://github.com/n8n-io/n8n/releases |
| Postgres 16 | 16.15 | `postgres:16.15-alpine` | Official-images library tags `16.15`, `16.15-alpine`, `16.15-alpine3.24` (2026-09-11). https://github.com/docker-library/official-images/blob/master/library/postgres |
| Redis 7.4 | 7.4.11 | `redis:7.4.11-alpine` | Official-images library tags `7.4.11-alpine`, `7.4-alpine`. https://github.com/docker-library/official-images/blob/master/library/redis |
| Mailpit | v1.31.1 | `axllent/mailpit:v1.31.1` | GitHub latest release v1.31.1 (2026-09-05). https://github.com/axllent/mailpit/releases Docker tags: https://hub.docker.com/r/axllent/mailpit/tags |
| dbmate | 2.35.1 | `amacneil/dbmate:2.35.1` | GitHub latest release v2.35.1 (2026-08-26). https://github.com/amacneil/dbmate/releases Docker Hub: https://hub.docker.com/r/amacneil/dbmate/tags |

n8n docs also publish `docker.n8n.io/n8nio/n8n:2.37.9`. Compose uses Docker Hub `n8nio/n8n:2.37.9` as required by PLT-T02/T03.

## Language runtimes (not in this compose file)

| Component | Pin | Source (2026-09-11) | Notes |
|---|---|---|---|
| Python | 3.12.14 | https://www.python.org/downloads/release/python-31214/ | Spec requires Python 3.12. 3.12.14 is a source-only security release. Docker Hub `python:3.12.x-alpine` patch TODO(verify) when service Dockerfiles land. |
| Go | 1.27.1 | https://go.dev/dl/ | Current stable on go.dev (1.27 released 2026-08-19; patch 1.27.1 listed as stable). |
| Node.js | 24.21.0 | https://nodejs.org/en/download | Active LTS (Krypton) for Code node snippet tests. https://github.com/nodejs/Release |

## n8n 2.0 breaking changes (read for this pin)

Source: https://docs.n8n.io/changelog/v20-breaking-changes.md

Effects on this stack:

- Queue mode stores binary data in the database by default. Compose sets `N8N_DEFAULT_BINARY_DATA_MODE=database`. Do not use in-memory `default` mode. Do not use S3/Azure (Enterprise). https://docs.n8n.io/deploy/host-n8n/configure-n8n/scaling/handle-binary-data.md
- Execute Command and LocalFileTrigger are excluded by default via `NODES_EXCLUDE`. Do not set `NODES_EXCLUDE=[]`.
- Code nodes cannot read process environment by default in 2.x (`N8N_BLOCK_ENV_ACCESS_IN_NODE=true` on the breaking-changes page). Do not set that variable to `false`. Compose sets `true` so the 2.x behaviour is explicit. The security env page still lists default `false`; see TODO(verify) below.
- Task runners are on by default. Compose sets `N8N_RUNNERS_ENABLED=true` to match the official Docker install example.
- MySQL/MariaDB are gone as n8n storage. This stack uses Postgres.
- Workflows use Publish, not the old Activate toggle. Import scripts in PLT-T07 must use `publish:workflow`.
- `WEBHOOK_URL` is documented as deprecated from n8n 2.35.0 (alias of `N8N_WEBHOOK_URL`). Pin 2.37.9 is after that. Compose sets both to the same value.
- `N8N_MULTI_MAIN_SETUP_ENABLED` is Enterprise. It is not set.
- Release channels are `stable` / `beta`. Still pin a numeric tag, never `stable` or `latest`.

## Queue mode docs used while pinning

- https://docs.n8n.io/deploy/host-n8n/configure-n8n/scaling/enable-queue-mode.md
- https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/queue-mode.md
- https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/nodes.md

## TODO(verify)

- Confirm `amacneil/dbmate:2.35.1` pulls from Docker Hub (GitHub release is v2.35.1; Hub also lists 2.35.0).
- `N8N_BLOCK_ENV_ACCESS_IN_NODE` default: breaking-changes page says `true` in 2.0; security env page still says default `false`. Compose sets `true`.
- `WEBHOOK_URL` vs `N8N_WEBHOOK_URL` on 2.37.9: both set. Confirm startup log if the alias still warns.
- n8n image `wget` for `/healthz` healthchecks. If 2.37.9 has no `wget`, switch the check to `node`.
- Mock service health path `/health` (mock-llm, flaky-api, review-ui). Dockerfiles are written in parallel (PLT-T05, PLT-T06, PLT-T10).
- Python Docker patch tag for 3.12 images when those Dockerfiles are written.
