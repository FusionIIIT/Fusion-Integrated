"""Financial status attestations are immutable even under bulk ORM SQL writes."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("hreis", "0003_financialstatusprojection")]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TRIGGER hreis_financial_status_immutable
                    BEFORE UPDATE OR DELETE ON hreis_financial_status
                    FOR EACH ROW EXECUTE FUNCTION hreis_reject_history_mutation();
            """,
            reverse_sql="""
                DROP TRIGGER IF EXISTS hreis_financial_status_immutable
                    ON hreis_financial_status;
            """,
        )
    ]
