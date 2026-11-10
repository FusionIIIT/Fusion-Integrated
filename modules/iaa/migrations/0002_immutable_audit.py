"""IAA-BR-502/503: block UPDATE and DELETE even through QuerySet/raw SQL."""
from django.db import migrations

FORWARD = """
CREATE FUNCTION iaa_reject_audit_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'IAA audit entries are append-only';
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER iaa_audit_append_only
BEFORE UPDATE OR DELETE ON iaa_audit_entry
FOR EACH ROW EXECUTE FUNCTION iaa_reject_audit_mutation();
"""
REVERSE = """
DROP TRIGGER IF EXISTS iaa_audit_append_only ON iaa_audit_entry;
DROP FUNCTION IF EXISTS iaa_reject_audit_mutation();
"""


class Migration(migrations.Migration):
    dependencies = [("iaa", "0001_initial")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
