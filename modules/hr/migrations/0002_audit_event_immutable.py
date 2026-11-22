from django.db import migrations


def install_audit_immutability(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("""
        CREATE OR REPLACE FUNCTION hr_reject_audit_event_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'HR audit events are immutable';
        END;
        $$
    """)
    schema_editor.execute("""
        CREATE TRIGGER hr_audit_event_immutable
        BEFORE UPDATE OR DELETE ON hr_audit_event
        FOR EACH ROW EXECUTE FUNCTION hr_reject_audit_event_mutation()
    """)


def remove_audit_immutability(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        "DROP TRIGGER IF EXISTS hr_audit_event_immutable ON hr_audit_event")
    schema_editor.execute(
        "DROP FUNCTION IF EXISTS hr_reject_audit_event_mutation()")


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            install_audit_immutability,
            reverse_code=remove_audit_immutability,
        ),
    ]
