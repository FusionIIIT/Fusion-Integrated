"""Protect historical HR records even against ORM bulk update/delete.

The assignment requires immutable audit, closed appraisal archives, and
ledger corrections as new reversing entries. Model save() hooks cannot protect
against QuerySet.update(); PostgreSQL triggers enforce the database invariant.
"""
from django.db import migrations


IMMUTABLE_TABLES = (
    "hreis_audit",
    "hreis_request_transition",
    "hreis_service_revision",
    "hreis_leave_ledger",
    "hreis_policy_version",
)

INSTALL_SQL = """
CREATE FUNCTION hreis_reject_history_mutation()
RETURNS trigger LANGUAGE plpgsql AS $hreis$
BEGIN
    RAISE EXCEPTION 'HR-EIS history is append-only (%).', TG_TABLE_NAME
        USING ERRCODE = '23514';
END;
$hreis$;

CREATE TRIGGER hreis_audit_immutable
    BEFORE UPDATE OR DELETE ON hreis_audit
    FOR EACH ROW EXECUTE FUNCTION hreis_reject_history_mutation();
CREATE TRIGGER hreis_transition_immutable
    BEFORE UPDATE OR DELETE ON hreis_request_transition
    FOR EACH ROW EXECUTE FUNCTION hreis_reject_history_mutation();
CREATE TRIGGER hreis_revision_immutable
    BEFORE UPDATE OR DELETE ON hreis_service_revision
    FOR EACH ROW EXECUTE FUNCTION hreis_reject_history_mutation();
CREATE TRIGGER hreis_ledger_immutable
    BEFORE UPDATE OR DELETE ON hreis_leave_ledger
    FOR EACH ROW EXECUTE FUNCTION hreis_reject_history_mutation();
CREATE TRIGGER hreis_policy_immutable
    BEFORE UPDATE OR DELETE ON hreis_policy_version
    FOR EACH ROW EXECUTE FUNCTION hreis_reject_history_mutation();

CREATE FUNCTION hreis_reject_finalized_appraisal_mutation()
RETURNS trigger LANGUAGE plpgsql AS $hreis$
BEGIN
    IF OLD.finalized_at IS NOT NULL THEN
        RAISE EXCEPTION 'Finalized appraisal is immutable.'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$hreis$;

CREATE TRIGGER hreis_appraisal_final_immutable
    BEFORE UPDATE OR DELETE ON hreis_appraisal
    FOR EACH ROW EXECUTE FUNCTION hreis_reject_finalized_appraisal_mutation();
"""

UNINSTALL_SQL = """
DROP TRIGGER IF EXISTS hreis_appraisal_final_immutable ON hreis_appraisal;
DROP TRIGGER IF EXISTS hreis_policy_immutable ON hreis_policy_version;
DROP TRIGGER IF EXISTS hreis_ledger_immutable ON hreis_leave_ledger;
DROP TRIGGER IF EXISTS hreis_revision_immutable ON hreis_service_revision;
DROP TRIGGER IF EXISTS hreis_transition_immutable ON hreis_request_transition;
DROP TRIGGER IF EXISTS hreis_audit_immutable ON hreis_audit;
DROP FUNCTION IF EXISTS hreis_reject_finalized_appraisal_mutation();
DROP FUNCTION IF EXISTS hreis_reject_history_mutation();
"""


class Migration(migrations.Migration):
    dependencies = [("hreis", "0001_initial")]

    operations = [
        migrations.RunSQL(sql=INSTALL_SQL, reverse_sql=UNINSTALL_SQL),
    ]
