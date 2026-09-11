-- Runs once on first Postgres data directory init
-- (official image: /docker-entrypoint-initdb.d).
-- POSTGRES_DB already creates database n8n when that env is set.
-- Create n8n and app if they are missing (psql \gexec).

SELECT format('CREATE DATABASE %I OWNER %I', 'n8n', current_user)
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'n8n')\gexec

SELECT format('CREATE DATABASE %I OWNER %I', 'app', current_user)
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'app')\gexec
