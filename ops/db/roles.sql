-- Run as the database administrator before AND after migrations.
-- This file manages only this service's roles, never the IAM database.
-- Credentials are provisioned separately; no passwords belong in source control.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'platform_migrator') THEN
        CREATE ROLE platform_migrator NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'platform_app') THEN
        CREATE ROLE platform_app NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
    END IF;
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO platform_app, platform_migrator', current_database());
END $$;

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO platform_migrator;
GRANT USAGE ON SCHEMA public TO platform_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO platform_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO platform_app;
ALTER DEFAULT PRIVILEGES FOR ROLE platform_migrator IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO platform_app;
ALTER DEFAULT PRIVILEGES FOR ROLE platform_migrator IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO platform_app;

DO $$
BEGIN
    IF to_regclass('public.visitor_hostel_auditevent') IS NOT NULL THEN
        REVOKE UPDATE, DELETE ON public.visitor_hostel_auditevent FROM platform_app;
    END IF;
    IF to_regclass('public.placement_application_transition') IS NOT NULL THEN
        REVOKE UPDATE, DELETE ON public.placement_application_transition FROM platform_app;
    END IF;
    IF to_regclass('public.vh_bill') IS NOT NULL THEN
        REVOKE UPDATE, DELETE ON public.vh_bill FROM platform_app;
        GRANT UPDATE (is_settled_offline, settlement_date, remarks, updated_at)
            ON public.vh_bill TO platform_app;
    END IF;
    IF to_regclass('public.visitor_hostel_roleassignment') IS NOT NULL THEN
        REVOKE INSERT, UPDATE, DELETE ON public.visitor_hostel_roleassignment FROM platform_app;
    END IF;
    IF to_regclass('public.django_migrations') IS NOT NULL THEN
        REVOKE INSERT, UPDATE, DELETE ON public.django_migrations FROM platform_app;
    END IF;
END $$;
