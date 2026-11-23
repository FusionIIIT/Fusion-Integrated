from django.db import migrations

# BR-PMS-122: the database itself refuses to change or delete an audit row.
FORWARD = """
CREATE OR REPLACE FUNCTION pms_auditentry_refuse_change() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'pms_auditentry rows are immutable';
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER pms_auditentry_immutable
    BEFORE UPDATE OR DELETE ON pms_auditentry
    FOR EACH ROW EXECUTE FUNCTION pms_auditentry_refuse_change();
"""
REVERSE = """
DROP TRIGGER IF EXISTS pms_auditentry_immutable ON pms_auditentry;
DROP FUNCTION IF EXISTS pms_auditentry_refuse_change();
"""


class Migration(migrations.Migration):
    dependencies = [("pms", "0001_initial")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
