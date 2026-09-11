-- migrate:up

-- Grant matrix (application roles). No DELETE on ops. No UPDATE or DELETE
-- on ops.audit_log for any application role.
--
-- table             n8n_app               app_backend            readonly
-- execution_log     SELECT, INSERT        SELECT, INSERT, UPDATE SELECT
-- idempotency_keys  SELECT, INSERT, UPDATE SELECT, INSERT, UPDATE SELECT
-- dead_letter       SELECT, INSERT, UPDATE SELECT, INSERT, UPDATE SELECT
-- review_queue      SELECT, INSERT, UPDATE SELECT, INSERT, UPDATE SELECT
-- audit_log         SELECT, INSERT        SELECT, INSERT         SELECT
-- incidents         SELECT, INSERT, UPDATE SELECT, INSERT, UPDATE SELECT

GRANT CONNECT ON DATABASE app TO n8n_app, app_backend, readonly;

GRANT USAGE ON SCHEMA ops TO n8n_app, app_backend, readonly;

GRANT SELECT, INSERT ON TABLE ops.execution_log TO n8n_app;
GRANT SELECT, INSERT, UPDATE ON TABLE ops.execution_log TO app_backend;

GRANT SELECT, INSERT, UPDATE ON TABLE ops.idempotency_keys TO n8n_app;
GRANT SELECT, INSERT, UPDATE ON TABLE ops.idempotency_keys TO app_backend;

GRANT SELECT, INSERT, UPDATE ON TABLE ops.dead_letter TO n8n_app;
GRANT SELECT, INSERT, UPDATE ON TABLE ops.dead_letter TO app_backend;

GRANT SELECT, INSERT, UPDATE ON TABLE ops.review_queue TO n8n_app;
GRANT SELECT, INSERT, UPDATE ON TABLE ops.review_queue TO app_backend;

GRANT SELECT, INSERT ON TABLE ops.audit_log TO n8n_app;
GRANT SELECT, INSERT ON TABLE ops.audit_log TO app_backend;

GRANT SELECT, INSERT, UPDATE ON TABLE ops.incidents TO n8n_app;
GRANT SELECT, INSERT, UPDATE ON TABLE ops.incidents TO app_backend;

GRANT SELECT ON TABLE
  ops.execution_log,
  ops.idempotency_keys,
  ops.dead_letter,
  ops.review_queue,
  ops.audit_log,
  ops.incidents
TO readonly;

GRANT USAGE, SELECT ON SEQUENCE ops.execution_log_id_seq TO n8n_app, app_backend;
GRANT USAGE, SELECT ON SEQUENCE ops.audit_log_id_seq TO n8n_app, app_backend;

REVOKE UPDATE, DELETE ON TABLE ops.audit_log FROM n8n_app;
REVOKE UPDATE, DELETE ON TABLE ops.audit_log FROM app_backend;
REVOKE UPDATE, DELETE ON TABLE ops.audit_log FROM readonly;
REVOKE UPDATE, DELETE ON TABLE ops.audit_log FROM PUBLIC;

REVOKE ALL ON TABLE ops.audit_log FROM PUBLIC;
REVOKE ALL ON SCHEMA ops FROM PUBLIC;

-- migrate:down

REVOKE USAGE, SELECT ON SEQUENCE ops.execution_log_id_seq FROM n8n_app, app_backend;
REVOKE USAGE, SELECT ON SEQUENCE ops.audit_log_id_seq FROM n8n_app, app_backend;

REVOKE ALL ON TABLE ops.execution_log FROM n8n_app, app_backend, readonly;
REVOKE ALL ON TABLE ops.idempotency_keys FROM n8n_app, app_backend, readonly;
REVOKE ALL ON TABLE ops.dead_letter FROM n8n_app, app_backend, readonly;
REVOKE ALL ON TABLE ops.review_queue FROM n8n_app, app_backend, readonly;
REVOKE ALL ON TABLE ops.audit_log FROM n8n_app, app_backend, readonly;
REVOKE ALL ON TABLE ops.incidents FROM n8n_app, app_backend, readonly;

REVOKE USAGE ON SCHEMA ops FROM n8n_app, app_backend, readonly;
REVOKE CONNECT ON DATABASE app FROM n8n_app, app_backend, readonly;
