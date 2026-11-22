from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("department", "0002_feedback_stockitem_stockrequest_stockmovement_notice_and_more")]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE FUNCTION department_prevent_movement_change() RETURNS trigger
                LANGUAGE plpgsql AS $$
                BEGIN
                    RAISE EXCEPTION 'Department stock movements are immutable'
                        USING ERRCODE = 'integrity_constraint_violation';
                END $$;
                CREATE TRIGGER department_stock_movement_immutable
                BEFORE UPDATE OR DELETE ON department_stockmovement
                FOR EACH ROW EXECUTE FUNCTION department_prevent_movement_change();
            """,
            reverse_sql="""
                DROP TRIGGER department_stock_movement_immutable ON department_stockmovement;
                DROP FUNCTION department_prevent_movement_change();
            """,
        ),
    ]
