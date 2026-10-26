from django.db import migrations


ENTITLEMENTS = {
    "CL": (["faculty", "staff"], {"faculty": "8.00", "staff": "8.00"}),
    "RH": (["faculty", "staff"], {"faculty": "2.00", "staff": "2.00"}),
    "SCL": (["faculty", "staff"], {"faculty": "15.00", "staff": "15.00"}),
    "EL": (["faculty", "staff"], {"faculty": "0.00", "staff": "30.00"}),
    "COL": (["faculty", "staff"], {"faculty": "20.00", "staff": "20.00"}),
    "VL": (["faculty"], {"faculty": "60.00"}),
}


def seed_entitlements(apps, schema_editor):
    LeavePolicy = apps.get_model("elm", "LeavePolicy")
    database = schema_editor.connection.alias
    for code, (kinds, values) in ENTITLEMENTS.items():
        LeavePolicy.objects.using(database).filter(
            leave_type_code=code
        ).update(
            employee_kinds=kinds,
            annual_entitlement_by_kind=values,
        )


class Migration(migrations.Migration):
    dependencies = [("elm", "0007_leavepolicy_annual_entitlement_by_kind")]
    operations = [
        migrations.RunPython(seed_entitlements, migrations.RunPython.noop),
    ]
