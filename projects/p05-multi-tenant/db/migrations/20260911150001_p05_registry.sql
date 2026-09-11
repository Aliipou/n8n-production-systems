-- migrate:up

-- Tenant registry. tenants and tenant_api_keys are used to establish
-- tenant context, so they are not RLS-filtered (see 20260911150003).
-- tenant_configs and tenant_secrets have tenant_id and get RLS.

CREATE TABLE p05.tenants (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text NOT NULL UNIQUE,
  name text NOT NULL,
  status text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT tenants_status_check
    CHECK (status IN ('active', 'disabled', 'deleted')),
  CONSTRAINT tenants_slug_check
    CHECK (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$' AND char_length(slug) BETWEEN 1 AND 63)
);

CREATE TABLE p05.tenant_configs (
  tenant_id uuid NOT NULL REFERENCES p05.tenants (id),
  version int NOT NULL,
  config jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by text,
  PRIMARY KEY (tenant_id, version),
  CONSTRAINT tenant_configs_version_check CHECK (version >= 1)
);

COMMENT ON TABLE p05.tenant_configs IS
  'Versioned tenant config. Never update a row in place; insert a new version.';

CREATE TABLE p05.tenant_api_keys (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES p05.tenants (id),
  key_hash text NOT NULL,
  prefix text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  revoked_at timestamptz,
  CONSTRAINT tenant_api_keys_prefix_check CHECK (char_length(prefix) = 8)
);

CREATE INDEX tenant_api_keys_tenant_id_idx
  ON p05.tenant_api_keys (tenant_id);

CREATE TABLE p05.tenant_secrets (
  tenant_id uuid NOT NULL REFERENCES p05.tenants (id),
  name text NOT NULL,
  ciphertext bytea NOT NULL,
  nonce bytea NOT NULL,
  key_version int NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, name),
  CONSTRAINT tenant_secrets_name_check
    CHECK (name IN ('crm_token', 'slack_webhook', 'smtp_password')),
  CONSTRAINT tenant_secrets_key_version_check CHECK (key_version >= 1)
);

COMMENT ON TABLE p05.tenant_secrets IS
  'AES-256-GCM ciphertext. Master key from TENANT_SECRETS_KEY. n8n never reads this table.';

-- migrate:down

DROP TABLE IF EXISTS p05.tenant_secrets;
DROP TABLE IF EXISTS p05.tenant_api_keys;
DROP TABLE IF EXISTS p05.tenant_configs;
DROP TABLE IF EXISTS p05.tenants;
