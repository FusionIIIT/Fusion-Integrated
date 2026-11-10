from django.db import migrations

FORWARD = """
CREATE FUNCTION iaa_guard_terminal_record() RETURNS trigger AS $$
BEGIN
    IF OLD.status = 'recorded' THEN
        RAISE EXCEPTION 'Recorded IAA financial requests are immutable';
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER iaa_recorded_immutable
BEFORE UPDATE OR DELETE ON iaa_financial_request
FOR EACH ROW EXECUTE FUNCTION iaa_guard_terminal_record();

CREATE FUNCTION iaa_guard_observation() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' OR OLD.status = 'closed' THEN
        RAISE EXCEPTION 'IAA audit observations must be retained; closed observations are immutable';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER iaa_observation_retained
BEFORE UPDATE OR DELETE ON iaa_observation
FOR EACH ROW EXECUTE FUNCTION iaa_guard_observation();
"""

REVERSE = """
DROP TRIGGER IF EXISTS iaa_recorded_immutable ON iaa_financial_request;
DROP FUNCTION IF EXISTS iaa_guard_terminal_record();
DROP TRIGGER IF EXISTS iaa_observation_retained ON iaa_observation;
DROP FUNCTION IF EXISTS iaa_guard_observation();
"""


class Migration(migrations.Migration):
    dependencies = [("iaa", "0002_immutable_audit")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
