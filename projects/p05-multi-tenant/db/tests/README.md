# P05 RLS tests

SQL files in this directory. Run after `dbmate` applies
`projects/p05-multi-tenant/db/migrations` to database `app`.

From the repository root (PowerShell):

```text
$env:DATABASE_URL = "postgres://n8n:change-me@127.0.0.1:5432/app?sslmode=disable"
psql $env:DATABASE_URL -v ON_ERROR_STOP=1 -f projects/p05-multi-tenant/db/tests/test_rls_no_context.sql
psql $env:DATABASE_URL -v ON_ERROR_STOP=1 -f projects/p05-multi-tenant/db/tests/test_rls_cross_read.sql
```

These tests are written before any P05 service uses the tables (spec P05-T02).
They are not a substitute for F01, F04 to F11.
