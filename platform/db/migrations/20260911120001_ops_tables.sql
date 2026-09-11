-- migrate:up

-- Columns match docs/specs/00-platform.md section 3.
-- created_at timestamptz is on every table (AGENTS.md SQL rule).

CREATE TABLE ops.execution_log (
  id bigserial PRIMARY KEY,
  ts timestamptz NOT NULL DEFAULT now(),
  correlation_id text NOT NULL,
  project text NOT NULL,
  workflow text NOT NULL,
  execution_id text,
  node text,
  level text,
  event text NOT NULL,
  data jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT execution_log_level_check
    CHECK (level IN ('debug', 'info', 'warn', 'error'))
);

CREATE INDEX execution_log_correlation_id_idx
  ON ops.execution_log (correlation_id);

CREATE INDEX execution_log_project_ts_idx
  ON ops.execution_log (project, ts);

CREATE TABLE ops.idempotency_keys (
  scope text NOT NULL,
  key text NOT NULL,
  first_seen_at timestamptz DEFAULT now(),
  execution_id text,
  status text,
  result jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (scope, key),
  CONSTRAINT idempotency_keys_status_check
    CHECK (status IN ('processing', 'done', 'failed'))
);

CREATE TABLE ops.dead_letter (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project text,
  workflow text,
  dependency text,
  retry_workflow_id text,
  payload jsonb,
  error_class text,
  error_message text,
  attempts integer,
  first_failed_at timestamptz,
  last_failed_at timestamptz,
  next_attempt_at timestamptz,
  status text,
  replayed_execution_id text,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT dead_letter_status_check
    CHECK (status IN ('pending_retry', 'dead', 'replayed', 'discarded'))
);

CREATE INDEX dead_letter_status_next_attempt_at_idx
  ON ops.dead_letter (status, next_attempt_at);

CREATE TABLE ops.review_queue (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project text,
  kind text,
  subject_id text,
  payload jsonb,
  status text,
  created_at timestamptz NOT NULL DEFAULT now(),
  decided_at timestamptz,
  decided_by text,
  decision jsonb,
  callback_workflow_id text,
  CONSTRAINT review_queue_status_check
    CHECK (status IN ('pending', 'approved', 'rejected', 'expired'))
);

CREATE INDEX review_queue_status_created_at_idx
  ON ops.review_queue (status, created_at);

CREATE TABLE ops.audit_log (
  id bigserial PRIMARY KEY,
  ts timestamptz NOT NULL DEFAULT now(),
  actor_type text,
  actor_id text,
  project text,
  action text,
  subject_type text,
  subject_id text,
  before jsonb,
  after jsonb,
  reason text,
  model text,
  prompt_version text,
  tokens_in integer,
  tokens_out integer,
  latency_ms integer,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT audit_log_actor_type_check
    CHECK (actor_type IN ('system', 'human', 'llm'))
);

COMMENT ON TABLE ops.audit_log IS
  'Append-only. Application roles get INSERT and SELECT only.';

CREATE TABLE ops.incidents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  fingerprint text,
  title text,
  severity text,
  status text,
  opened_at timestamptz,
  resolved_at timestamptz,
  details jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT incidents_status_check
    CHECK (status IN ('open', 'resolved'))
);

CREATE UNIQUE INDEX incidents_fingerprint_open_uidx
  ON ops.incidents (fingerprint)
  WHERE status = 'open';

-- migrate:down

DROP TABLE IF EXISTS ops.incidents;
DROP TABLE IF EXISTS ops.audit_log;
DROP TABLE IF EXISTS ops.review_queue;
DROP TABLE IF EXISTS ops.dead_letter;
DROP TABLE IF EXISTS ops.idempotency_keys;
DROP TABLE IF EXISTS ops.execution_log;
