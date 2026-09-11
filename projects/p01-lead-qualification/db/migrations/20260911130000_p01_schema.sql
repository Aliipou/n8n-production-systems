-- migrate:up

CREATE SCHEMA IF NOT EXISTS p01;

CREATE TABLE p01.leads (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  correlation_id text,
  email_normalized citext UNIQUE,
  name text,
  company_name text,
  company_domain text,
  is_free_mail boolean,
  country text,
  language text,
  consent_marketing boolean,
  consent_ts timestamptz,
  status text,
  score int,
  score_breakdown jsonb,
  route text,
  llm_status text,
  crm_id text,
  crm_sync_status text,
  owner text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE p01.submissions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id uuid REFERENCES p01.leads (id),
  submission_id text UNIQUE,
  raw_payload jsonb,
  ip_hash text,
  received_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE p01.settings (
  key text PRIMARY KEY,
  value jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE EXTENSION IF NOT EXISTS citext;

-- migrate:down

DROP SCHEMA IF EXISTS p01 CASCADE;
