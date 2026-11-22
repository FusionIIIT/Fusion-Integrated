from django.db import migrations


def reconcile_missing_tables(apps, schema_editor):
    existing = set(schema_editor.connection.introspection.table_names())
    names = (
        "LeavePolicy", "Employee", "HolidayCalendar", "Unit", "LeaveApplication",
        "AssignmentNotification", "SubstituteResponse", "HolidayDate", "LeaveUsage",
    )
    for name in names:
        model = apps.get_model("elm", name)
        if model._meta.db_table not in existing:
            schema_editor.create_model(model)
            existing.add(model._meta.db_table)


class Migration(migrations.Migration):
    dependencies = [("elm", "0001_initial")]
    operations = [migrations.RunPython(reconcile_missing_tables, migrations.RunPython.noop)]
