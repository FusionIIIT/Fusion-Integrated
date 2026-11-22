from django.db import migrations

APPEND_ONLY = ("phc_audit_record", "phc_claim_action", "phc_stock_adjustment",
               "phc_low_stock_alert", "phc_notification", "phc_reimbursement_policy")

FUNCTION = """
CREATE OR REPLACE FUNCTION phc_refuse_change() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION '% rows are append-only', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION phc_freeze_claim() RETURNS trigger AS $$
BEGIN
    IF (NEW.user_id, NEW.prescription_id, NEW.expense_date, NEW.amount, NEW.description,
        NEW.submitted_at) IS DISTINCT FROM (OLD.user_id, OLD.prescription_id,
        OLD.expense_date, OLD.amount, OLD.description, OLD.submitted_at) THEN
        RAISE EXCEPTION 'a submitted reimbursement claim cannot be edited';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

# PHC-BR-09 and PHC-BR-14 hold even against a shell or a buggy service.
forward = [FUNCTION] + [
    f"CREATE TRIGGER {t}_append_only BEFORE UPDATE OR DELETE ON {t} "
    f"FOR EACH ROW EXECUTE FUNCTION phc_refuse_change();" for t in APPEND_ONLY
] + [
    "CREATE TRIGGER phc_reimbursement_claim_frozen BEFORE UPDATE ON phc_reimbursement_claim "
    "FOR EACH ROW EXECUTE FUNCTION phc_freeze_claim();",
    "CREATE TRIGGER phc_reimbursement_claim_no_delete BEFORE DELETE ON "
    "phc_reimbursement_claim FOR EACH ROW EXECUTE FUNCTION phc_refuse_change();",
]

backward = [f"DROP TRIGGER IF EXISTS {t}_append_only ON {t};" for t in APPEND_ONLY] + [
    "DROP TRIGGER IF EXISTS phc_reimbursement_claim_frozen ON phc_reimbursement_claim;",
    "DROP TRIGGER IF EXISTS phc_reimbursement_claim_no_delete ON phc_reimbursement_claim;",
    "DROP FUNCTION IF EXISTS phc_freeze_claim();",
    "DROP FUNCTION IF EXISTS phc_refuse_change();",
]


class Migration(migrations.Migration):
    dependencies = [("phc", "0001_initial")]

    operations = [migrations.RunSQL(sql=forward, reverse_sql=backward)]
