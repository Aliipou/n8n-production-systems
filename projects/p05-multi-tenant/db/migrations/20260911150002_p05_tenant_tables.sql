-- migrate:up

-- Tenant-scoped copies of the P01 tables listed in docs/specs/05-multi-tenant.md.
-- Each row has tenant_id NOT NULL. Unique keys are per tenant.

CREATE TABLE p05.leads (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES p05.tenants (id),
  correlation_id text,
  email_normalized citext,
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
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, email_normalized),
  CONSTRAINT leads_language_check
    CHECK (language IS NULL OR language IN ('fi', 'sv', 'en', 'other')),
  CONSTRAINT leads_status_check
    CHECK (
      status IS NULL OR status IN (
        'new', 'qualified', 'nurture', 'archived', 'contacted', 'replied',
        'meeting_booked', 'unsubscribed', 'bounced', 'invalid', 'spam'
      )
    ),
  CONSTRAINT leads_crm_sync_status_check
    CHECK (
      crm_sync_status IS NULL
      OR crm_sync_status IN ('pending', 'synced', 'failed')
    )
);

CREATE INDEX leads_tenant_id_created_at_idx
  ON p05.leads (tenant_id, created_at);

CREATE TABLE p05.submissions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES p05.tenants (id),
  lead_id uuid NOT NULL,
  submission_id text,
  raw_payload jsonb,
  ip_hash text,
  received_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, submission_id),
  FOREIGN KEY (tenant_id, lead_id)
    REFERENCES p05.leads (tenant_id, id)
);

CREATE TABLE p05.email_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES p05.tenants (id),
  lead_id uuid NOT NULL,
  kind text,
  language text,
  subject text,
  draft_text text,
  final_text text,
  status text,
  review_id text,
  smtp_message_id text,
  sent_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (tenant_id, lead_id)
    REFERENCES p05.leads (tenant_id, id),
  CONSTRAINT email_messages_kind_check
    CHECK (
      kind IS NULL OR kind IN ('first_contact', 'followup', 'nurture')
    ),
  CONSTRAINT email_messages_status_check
    CHECK (
      status IS NULL OR status IN (
        'draft', 'pending_approval', 'approved', 'rejected',
        'sending', 'sent', 'bounced', 'failed'
      )
    )
);

CREATE TABLE p05.followups (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES p05.tenants (id),
  lead_id uuid NOT NULL,
  step int,
  due_at timestamptz,
  status text,
  cancel_reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (tenant_id, lead_id)
    REFERENCES p05.leads (tenant_id, id),
  CONSTRAINT followups_status_check
    CHECK (
      status IS NULL OR status IN ('scheduled', 'sent', 'cancelled')
    )
);

CREATE INDEX followups_tenant_status_due_at_idx
  ON p05.followups (tenant_id, status, due_at);

CREATE TABLE p05.suppression_list (
  tenant_id uuid NOT NULL REFERENCES p05.tenants (id),
  email_normalized citext NOT NULL,
  reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, email_normalized),
  CONSTRAINT suppression_list_reason_check
    CHECK (
      reason IS NULL OR reason IN ('unsubscribed', 'bounced', 'manual')
    )
);

CREATE TABLE p05.activities (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES p05.tenants (id),
  lead_id uuid,
  type text,
  data jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (tenant_id, lead_id)
    REFERENCES p05.leads (tenant_id, id)
);

CREATE TABLE p05.llm_calls (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES p05.tenants (id),
  lead_id uuid,
  purpose text,
  prompt_version text,
  model text,
  output jsonb,
  valid boolean,
  error text,
  tokens_in integer,
  tokens_out integer,
  latency_ms integer,
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (tenant_id, lead_id)
    REFERENCES p05.leads (tenant_id, id),
  CONSTRAINT llm_calls_purpose_check
    CHECK (
      purpose IS NULL OR purpose IN ('classify', 'draft_email')
    )
);

-- migrate:down

DROP TABLE IF EXISTS p05.llm_calls;
DROP TABLE IF EXISTS p05.activities;
DROP TABLE IF EXISTS p05.suppression_list;
DROP TABLE IF EXISTS p05.followups;
DROP TABLE IF EXISTS p05.email_messages;
DROP TABLE IF EXISTS p05.submissions;
DROP TABLE IF EXISTS p05.leads;
