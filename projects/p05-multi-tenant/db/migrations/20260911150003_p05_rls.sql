-- migrate:up

-- Row-level security. Application role p05_backend has NOBYPASSRLS.
-- Policy expression matches docs/specs/05-multi-tenant.md:
--   tenant_id = current_setting('app.tenant_id')::uuid
--
-- tenants and tenant_api_keys are used to resolve slug/key before the GUC
-- is set, so they are granted without RLS. All other p05 tables enable RLS.
-- n8n_app is not granted on p05 (n8n must not query tenant tables).

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA p05 TO p05_backend;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA p05 TO p05_backend;

ALTER DEFAULT PRIVILEGES IN SCHEMA p05
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO p05_backend;

ALTER DEFAULT PRIVILEGES IN SCHEMA p05
  GRANT USAGE, SELECT ON SEQUENCES TO p05_backend;

-- Registry lookup (no RLS): tenants, tenant_api_keys.
-- RLS on: tenant_configs, tenant_secrets, and all P01 copies.

ALTER TABLE p05.tenant_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE p05.tenant_secrets ENABLE ROW LEVEL SECURITY;
ALTER TABLE p05.leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE p05.submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE p05.email_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE p05.followups ENABLE ROW LEVEL SECURITY;
ALTER TABLE p05.suppression_list ENABLE ROW LEVEL SECURITY;
ALTER TABLE p05.activities ENABLE ROW LEVEL SECURITY;
ALTER TABLE p05.llm_calls ENABLE ROW LEVEL SECURITY;

-- FORCE so the table owner is also subject unless it is a superuser or
-- has BYPASSRLS. p05_backend has neither.
ALTER TABLE p05.tenant_configs FORCE ROW LEVEL SECURITY;
ALTER TABLE p05.tenant_secrets FORCE ROW LEVEL SECURITY;
ALTER TABLE p05.leads FORCE ROW LEVEL SECURITY;
ALTER TABLE p05.submissions FORCE ROW LEVEL SECURITY;
ALTER TABLE p05.email_messages FORCE ROW LEVEL SECURITY;
ALTER TABLE p05.followups FORCE ROW LEVEL SECURITY;
ALTER TABLE p05.suppression_list FORCE ROW LEVEL SECURITY;
ALTER TABLE p05.activities FORCE ROW LEVEL SECURITY;
ALTER TABLE p05.llm_calls FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_configs_isolation ON p05.tenant_configs
  FOR ALL TO p05_backend
  USING (tenant_id = current_setting('app.tenant_id')::uuid)
  WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

CREATE POLICY tenant_secrets_isolation ON p05.tenant_secrets
  FOR ALL TO p05_backend
  USING (tenant_id = current_setting('app.tenant_id')::uuid)
  WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

CREATE POLICY leads_isolation ON p05.leads
  FOR ALL TO p05_backend
  USING (tenant_id = current_setting('app.tenant_id')::uuid)
  WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

CREATE POLICY submissions_isolation ON p05.submissions
  FOR ALL TO p05_backend
  USING (tenant_id = current_setting('app.tenant_id')::uuid)
  WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

CREATE POLICY email_messages_isolation ON p05.email_messages
  FOR ALL TO p05_backend
  USING (tenant_id = current_setting('app.tenant_id')::uuid)
  WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

CREATE POLICY followups_isolation ON p05.followups
  FOR ALL TO p05_backend
  USING (tenant_id = current_setting('app.tenant_id')::uuid)
  WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

CREATE POLICY suppression_list_isolation ON p05.suppression_list
  FOR ALL TO p05_backend
  USING (tenant_id = current_setting('app.tenant_id')::uuid)
  WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

CREATE POLICY activities_isolation ON p05.activities
  FOR ALL TO p05_backend
  USING (tenant_id = current_setting('app.tenant_id')::uuid)
  WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

CREATE POLICY llm_calls_isolation ON p05.llm_calls
  FOR ALL TO p05_backend
  USING (tenant_id = current_setting('app.tenant_id')::uuid)
  WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

-- migrate:down

DROP POLICY IF EXISTS llm_calls_isolation ON p05.llm_calls;
DROP POLICY IF EXISTS activities_isolation ON p05.activities;
DROP POLICY IF EXISTS suppression_list_isolation ON p05.suppression_list;
DROP POLICY IF EXISTS followups_isolation ON p05.followups;
DROP POLICY IF EXISTS email_messages_isolation ON p05.email_messages;
DROP POLICY IF EXISTS submissions_isolation ON p05.submissions;
DROP POLICY IF EXISTS leads_isolation ON p05.leads;
DROP POLICY IF EXISTS tenant_secrets_isolation ON p05.tenant_secrets;
DROP POLICY IF EXISTS tenant_configs_isolation ON p05.tenant_configs;

ALTER TABLE p05.llm_calls NO FORCE ROW LEVEL SECURITY;
ALTER TABLE p05.activities NO FORCE ROW LEVEL SECURITY;
ALTER TABLE p05.suppression_list NO FORCE ROW LEVEL SECURITY;
ALTER TABLE p05.followups NO FORCE ROW LEVEL SECURITY;
ALTER TABLE p05.email_messages NO FORCE ROW LEVEL SECURITY;
ALTER TABLE p05.submissions NO FORCE ROW LEVEL SECURITY;
ALTER TABLE p05.leads NO FORCE ROW LEVEL SECURITY;
ALTER TABLE p05.tenant_secrets NO FORCE ROW LEVEL SECURITY;
ALTER TABLE p05.tenant_configs NO FORCE ROW LEVEL SECURITY;

ALTER TABLE p05.llm_calls DISABLE ROW LEVEL SECURITY;
ALTER TABLE p05.activities DISABLE ROW LEVEL SECURITY;
ALTER TABLE p05.suppression_list DISABLE ROW LEVEL SECURITY;
ALTER TABLE p05.followups DISABLE ROW LEVEL SECURITY;
ALTER TABLE p05.email_messages DISABLE ROW LEVEL SECURITY;
ALTER TABLE p05.submissions DISABLE ROW LEVEL SECURITY;
ALTER TABLE p05.leads DISABLE ROW LEVEL SECURITY;
ALTER TABLE p05.tenant_secrets DISABLE ROW LEVEL SECURITY;
ALTER TABLE p05.tenant_configs DISABLE ROW LEVEL SECURITY;

ALTER DEFAULT PRIVILEGES IN SCHEMA p05
  REVOKE USAGE, SELECT ON SEQUENCES FROM p05_backend;
ALTER DEFAULT PRIVILEGES IN SCHEMA p05
  REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM p05_backend;

REVOKE USAGE, SELECT ON ALL SEQUENCES IN SCHEMA p05 FROM p05_backend;
REVOKE SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA p05 FROM p05_backend;
