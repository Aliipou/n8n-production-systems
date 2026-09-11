-- migrate:up

-- gen_random_uuid() is used as the default for UUID primary keys.
-- Postgres 13+ ships gen_random_uuid in core; enable pgcrypto as well so
-- the function is present on images that still expose it only via that
-- extension. TODO(verify): confirm gen_random_uuid() on the pinned Postgres
-- image in PLT-T03 (16 vs 17 is still open in docs/QUESTIONS.md).
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA ops;

COMMENT ON SCHEMA ops IS 'Shared operational tables for all projects (database app).';

-- migrate:down

DROP SCHEMA IF EXISTS ops CASCADE;
DROP EXTENSION IF EXISTS pgcrypto;
