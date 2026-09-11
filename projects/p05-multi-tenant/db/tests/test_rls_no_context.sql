-- F02: query without tenant context must not return tenant rows.
-- Run as the migrate superuser after dbmate up against database app:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f projects/p05-multi-tenant/db/tests/test_rls_no_context.sql
--
-- Expectation: p05_backend has NOBYPASSRLS. SELECT on p05.leads without
-- app.tenant_id fails closed (unrecognized GUC or zero rows). No lead is
-- visible. The application is expected to log the error.

DO $$
DECLARE
  tenant_a uuid;
  lead_a uuid;
  n bigint;
  bypass boolean;
  saw_closed boolean := false;
BEGIN
  SELECT rolbypassrls INTO bypass
  FROM pg_roles
  WHERE rolname = 'p05_backend';

  IF bypass IS DISTINCT FROM false THEN
    RAISE EXCEPTION 'p05_backend must have rolbypassrls = false, got %', bypass;
  END IF;

  INSERT INTO p05.tenants (slug, name, status)
  VALUES ('rls-f02-a', 'RLS F02 Tenant A', 'active')
  RETURNING id INTO tenant_a;

  INSERT INTO p05.leads (tenant_id, email_normalized, status)
  VALUES (tenant_a, 'f02-a@rls.example.test', 'new')
  RETURNING id INTO lead_a;

  EXECUTE 'SET LOCAL ROLE p05_backend';

  BEGIN
    SELECT count(*) INTO n FROM p05.leads;
    IF n <> 0 THEN
      RAISE EXCEPTION 'F02: expected zero rows without tenant context, got %', n;
    END IF;
    saw_closed := true;
  EXCEPTION
    WHEN undefined_object THEN
      -- current_setting('app.tenant_id') with GUC unset
      saw_closed := true;
    WHEN invalid_text_representation THEN
      saw_closed := true;
  END;

  EXECUTE 'RESET ROLE';

  IF NOT saw_closed THEN
    RAISE EXCEPTION 'F02: expected fail-closed SELECT on p05.leads without app.tenant_id';
  END IF;

  DELETE FROM p05.leads WHERE id = lead_a;
  DELETE FROM p05.tenants WHERE id = tenant_a;
EXCEPTION
  WHEN OTHERS THEN
    EXECUTE 'RESET ROLE';
    DELETE FROM p05.leads WHERE email_normalized = 'f02-a@rls.example.test';
    DELETE FROM p05.tenants WHERE slug = 'rls-f02-a';
    RAISE;
END
$$;
