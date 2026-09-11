-- Append-only check for ops.audit_log.
-- Run as the migrate superuser (POSTGRES_USER) after dbmate up:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f platform/db/tests/test_audit_append_only.sql
-- Expectation: UPDATE (and DELETE) as app_backend fail with insufficient_privilege.

DO $$
DECLARE
  new_id bigint;
BEGIN
  EXECUTE 'SET LOCAL ROLE app_backend';

  INSERT INTO ops.audit_log (
    actor_type, actor_id, project, action, subject_type, subject_id
  )
  VALUES (
    'system', 'plt-t04-grants-sql', 'platform', 'test.audit_append_only',
    'test', 'plt-t04'
  )
  RETURNING id INTO new_id;

  BEGIN
    UPDATE ops.audit_log SET reason = 'should-fail' WHERE id = new_id;
    RAISE EXCEPTION 'expected UPDATE on ops.audit_log as app_backend to fail';
  EXCEPTION
    WHEN insufficient_privilege THEN
      NULL;
  END;

  BEGIN
    DELETE FROM ops.audit_log WHERE id = new_id;
    RAISE EXCEPTION 'expected DELETE on ops.audit_log as app_backend to fail';
  EXCEPTION
    WHEN insufficient_privilege THEN
      NULL;
  END;

  EXECUTE 'RESET ROLE';
  DELETE FROM ops.audit_log WHERE actor_id = 'plt-t04-grants-sql';
END
$$;
