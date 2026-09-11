-- F03: tenant A context reading tenant B's lead id returns zero rows.
-- Also checks WITH CHECK: insert with B's tenant_id under A's GUC fails.
-- Run as the migrate superuser after dbmate up against database app:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f projects/p05-multi-tenant/db/tests/test_rls_cross_read.sql

DO $$
DECLARE
  tenant_a uuid;
  tenant_b uuid;
  lead_b uuid;
  n bigint;
  insert_blocked boolean := false;
BEGIN
  INSERT INTO p05.tenants (slug, name, status)
  VALUES ('rls-f03-a', 'RLS F03 Tenant A', 'active')
  RETURNING id INTO tenant_a;

  INSERT INTO p05.tenants (slug, name, status)
  VALUES ('rls-f03-b', 'RLS F03 Tenant B', 'active')
  RETURNING id INTO tenant_b;

  INSERT INTO p05.leads (tenant_id, email_normalized, status)
  VALUES (tenant_b, 'f03-b@rls.example.test', 'new')
  RETURNING id INTO lead_b;

  PERFORM set_config('app.tenant_id', tenant_a::text, true);
  EXECUTE 'SET LOCAL ROLE p05_backend';

  SELECT count(*) INTO n FROM p05.leads WHERE id = lead_b;
  IF n <> 0 THEN
    RAISE EXCEPTION 'F03: tenant A context leaked tenant B lead, count=%', n;
  END IF;

  SELECT count(*) INTO n FROM p05.leads;
  IF n <> 0 THEN
    RAISE EXCEPTION 'F03: tenant A context saw unexpected leads, count=%', n;
  END IF;

  BEGIN
    INSERT INTO p05.leads (tenant_id, email_normalized, status)
    VALUES (tenant_b, 'f03-evil@rls.example.test', 'new');
    RAISE EXCEPTION 'F03: expected WITH CHECK to block insert of tenant B row under tenant A GUC';
  EXCEPTION
    WHEN insufficient_privilege THEN
      insert_blocked := true;
  END;

  IF NOT insert_blocked THEN
    RAISE EXCEPTION 'F03: cross-tenant insert was not blocked';
  END IF;

  EXECUTE 'RESET ROLE';

  DELETE FROM p05.leads WHERE tenant_id IN (tenant_a, tenant_b);
  DELETE FROM p05.tenants WHERE id IN (tenant_a, tenant_b);
EXCEPTION
  WHEN OTHERS THEN
    EXECUTE 'RESET ROLE';
    DELETE FROM p05.leads
    WHERE email_normalized IN (
      'f03-b@rls.example.test',
      'f03-evil@rls.example.test'
    );
    DELETE FROM p05.tenants WHERE slug IN ('rls-f03-a', 'rls-f03-b');
    RAISE;
END
$$;
