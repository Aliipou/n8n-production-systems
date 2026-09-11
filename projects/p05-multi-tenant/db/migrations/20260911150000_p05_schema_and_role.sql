-- migrate:up

-- Schema p05, extensions, and the application role used after tenant
-- context is set. The role has no BYPASSRLS (explicit).
-- Password is the local placeholder from .env.example (change-me).
-- Production must rotate it. Do not put real secrets in this file.

CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS p05;

CREATE ROLE p05_backend LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT NOBYPASSRLS
  PASSWORD 'change-me';

COMMENT ON ROLE p05_backend IS
  'P05 tenant backend and tenantctl. NOBYPASSRLS. Sets app.tenant_id before queries.';

GRANT USAGE ON SCHEMA p05 TO p05_backend;

-- migrate:down

REVOKE USAGE ON SCHEMA p05 FROM p05_backend;
DROP ROLE IF EXISTS p05_backend;
DROP SCHEMA IF EXISTS p05 CASCADE;
