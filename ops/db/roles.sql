-- Idempotent database roles and grants. Re-run on every deploy so a new table
-- cannot silently inherit privileges broader than the application role.
-- Passwords are supplied by the environment at provision time, never here.

DO $roles$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'platform_app') THEN
        CREATE ROLE platform_app NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'platform_migrator') THEN
        CREATE ROLE platform_migrator NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'platform_erp_ro') THEN
        CREATE ROLE platform_erp_ro NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sysops_app') THEN
        CREATE ROLE sysops_app NOLOGIN;
    END IF;
END
$roles$;

-- PHC tables. The audit trail is append-only: platform_app may insert but may
-- not update or delete history, which is what PHC-BR-09 requires.
DO $tables$
DECLARE
    t text;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'phc_doctor_schedule', 'phc_doctor_attendance', 'phc_patient',
        'phc_visit', 'phc_prescription', 'phc_reimbursement_claim',
        'phc_inventory_item', 'phc_stock_adjustment', 'phc_requisition',
        'phc_requisition_item', 'phc_ambulance_log', 'phc_health_advisory',
        'phc_notification_outbox'
    ]
    LOOP
        IF to_regclass(format('public.%I', t)) IS NULL THEN
            CONTINUE;
        END IF;
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON %I TO platform_app', t);
        EXECUTE format('GRANT SELECT ON %I TO sysops_app', t);
        EXECUTE format('GRANT SELECT ON %I TO platform_erp_ro', t);
        EXECUTE format('GRANT ALL ON %I TO platform_migrator', t);
    END LOOP;
END
$tables$;

DO $audit$
BEGIN
    IF to_regclass('public.phc_audit_log') IS NOT NULL THEN
        REVOKE UPDATE, DELETE ON phc_audit_log FROM platform_app;
        GRANT SELECT, INSERT ON phc_audit_log TO platform_app;
        GRANT SELECT ON phc_audit_log TO sysops_app;
        GRANT ALL ON phc_audit_log TO platform_migrator;
    END IF;
END
$audit$;

GRANT USAGE ON SCHEMA public TO platform_app, sysops_app, platform_erp_ro, platform_migrator;
