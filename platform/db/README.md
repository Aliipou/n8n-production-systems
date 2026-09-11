# Platform database (`ops` in `app`)

Shared schema for execution logs, idempotency, DLQ, review queue, audit, and incidents. Project schemas (`p01` to `p05`) live in `projects/<p>/db/migrations` and are applied against the same `app` database.

## How dbmate runs

Migrations are plain SQL in `platform/db/migrations/`. dbmate records applied versions in table `schema_migrations`.

Set `DATABASE_URL` to database `app` (not `n8n`). SSL is off for local compose.

From the repository root (PowerShell):

```text
$env:DATABASE_URL = "postgres://n8n:change-me@127.0.0.1:5432/app?sslmode=disable"
dbmate --migrations-dir platform/db/migrations --no-dump-schema up
```

Unix: `export DATABASE_URL=postgres://n8n:change-me@127.0.0.1:5432/app?sslmode=disable`. cmd.exe: `set DATABASE_URL=...` on the same line as the dbmate command.

Useful commands:

```text
dbmate --migrations-dir platform/db/migrations --no-dump-schema status
dbmate --migrations-dir platform/db/migrations --no-dump-schema up
dbmate --migrations-dir platform/db/migrations --no-dump-schema down
```

`--no-dump-schema` avoids writing a generated `schema.sql` at the default path. `--migrations-dir` is required because dbmate defaults to `./db/migrations`.

The one-shot `migrate` service in compose (PLT-T03) should mount this directory and run `dbmate --wait --no-dump-schema up` with `DATABASE_URL` pointing at host `postgres`, database `app`, user `POSTGRES_USER`.

TODO(verify): pin the dbmate image tag (and digest) in compose. Current GitHub release observed 2026-09-11: `ghcr.io/amacneil/dbmate:2.35.0`.

## Roles and passwords

Created by migration `20260911120002_ops_roles.sql`:

| Role | Used by | Privileges on `ops` |
|---|---|---|
| `n8n_app` | n8n Postgres credential | INSERT/SELECT, plus UPDATE where workflows mutate rows. No UPDATE/DELETE on `audit_log`. No DELETE on `ops`. |
| `app_backend` | Python and Go backends | INSERT/SELECT/UPDATE on `ops`. `audit_log` is INSERT+SELECT only. |
| `readonly` | dashboards | SELECT only |

Local role passwords are the placeholder `change-me` (same as `.env.example`). Production must rotate them. Do not put real secrets in migrations.

If compose later introduces `N8N_APP_PASSWORD` and `APP_BACKEND_PASSWORD`, keep this SQL placeholder for local boots, or replace the role migration with an init script that reads those env vars. Do not commit the values.

The table owner (migrate user, `POSTGRES_USER`) still has full rights on `audit_log`. Application roles do not.

## Grants test

Pytest (skipped unless `DATABASE_URL` is set):

```text
$env:DATABASE_URL = "postgres://n8n:change-me@127.0.0.1:5432/app?sslmode=disable"
pytest platform/db/tests/test_grants.py
```

Needs `psycopg` 3. Optional env overrides: `N8N_APP_PASSWORD`, `APP_BACKEND_PASSWORD`, `READONLY_PASSWORD` (default `change-me`).

Equivalent SQL (superuser URL, uses `SET ROLE app_backend`):

```text
psql $env:DATABASE_URL -v ON_ERROR_STOP=1 -f platform/db/tests/test_audit_append_only.sql
```

`UPDATE` and `DELETE` on `ops.audit_log` as `app_backend` must fail with `insufficient_privilege`.
