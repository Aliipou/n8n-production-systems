-- migrate:up

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS p03;

CREATE TABLE p03.inbox_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source text NOT NULL,
    external_event_id text NOT NULL,
    event_type text NOT NULL,
    source_ts timestamptz,
    received_at timestamptz NOT NULL DEFAULT now(),
    headers jsonb NOT NULL DEFAULT '{}'::jsonb,
    payload jsonb,
    status text NOT NULL DEFAULT 'pending'
        CHECK (status IN (
            'pending',
            'dispatched',
            'processed',
            'failed',
            'dead',
            'ignored',
            'discarded'
        )),
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    next_attempt_at timestamptz NOT NULL DEFAULT now(),
    dispatched_at timestamptz,
    processed_at timestamptz,
    last_error text,
    replay_of uuid REFERENCES p03.inbox_events (id),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source, external_event_id)
);

COMMENT ON COLUMN p03.inbox_events.payload IS
    'Raw provider JSON. Retention 30 days. Purge job nulls payload and keeps metadata.';

CREATE INDEX inbox_events_status_next_attempt_at_idx
    ON p03.inbox_events (status, next_attempt_at);

CREATE INDEX inbox_events_received_at_idx
    ON p03.inbox_events (received_at);

CREATE TABLE p03.customers (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source text NOT NULL,
    external_id text NOT NULL,
    email_hash text,
    name text,
    last_source_ts timestamptz,
    data jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source, external_id)
);

CREATE TABLE p03.fulfilment_requests (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_key text NOT NULL UNIQUE,
    status text NOT NULL DEFAULT 'created',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE p03.repo_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    delivery_id text NOT NULL UNIQUE,
    repo text NOT NULL,
    ref text,
    commits integer NOT NULL DEFAULT 0 CHECK (commits >= 0),
    pushed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE p03.processed_effects (
    effect_key text PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now()
);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_backend') THEN
        GRANT USAGE ON SCHEMA p03 TO app_backend;
        GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA p03 TO app_backend;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA p03 TO app_backend;
        ALTER DEFAULT PRIVILEGES IN SCHEMA p03
            GRANT SELECT, INSERT, UPDATE ON TABLES TO app_backend;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'n8n_app') THEN
        GRANT USAGE ON SCHEMA p03 TO n8n_app;
        GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA p03 TO n8n_app;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'readonly') THEN
        GRANT USAGE ON SCHEMA p03 TO readonly;
        GRANT SELECT ON ALL TABLES IN SCHEMA p03 TO readonly;
    END IF;
END
$$;

-- migrate:down

DROP SCHEMA IF EXISTS p03 CASCADE;
