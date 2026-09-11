-- migrate:up

-- Application roles for database app. Passwords are the local placeholder
-- from .env.example (change-me). Production must rotate these before any
-- network exposure. Do not put real secrets in this file.
--
-- n8n_app: n8n Postgres credential targeting schema ops (not n8n's own DB).
-- app_backend: Python and Go backends.
-- readonly: dashboards and ad-hoc SELECT.

CREATE ROLE n8n_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT
  PASSWORD 'change-me';

CREATE ROLE app_backend LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT
  PASSWORD 'change-me';

CREATE ROLE readonly LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT
  PASSWORD 'change-me';

-- migrate:down

DROP ROLE IF EXISTS n8n_app;
DROP ROLE IF EXISTS app_backend;
DROP ROLE IF EXISTS readonly;
