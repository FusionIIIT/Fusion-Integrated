from decimal import Decimal

from django.db import migrations


POLICIES = (
    ("CL", ["faculty", "staff"], "8.00", "WORKING_DAYS", False, True, False, "", "1.00"),
    ("RH", ["faculty", "staff"], "2.00", "RH_DATE", False, False, False, "", "1.00"),
    ("SCL", ["faculty", "staff"], "15.00", "WORKING_DAYS", False, False, False, "", "1.00"),
    ("EL", ["staff"], "30.00", "CALENDAR_DAYS", True, False, False, "", "1.00"),
    ("COL", ["faculty", "staff"], "20.00", "CALENDAR_DAYS", True, False, False, "", "1.00"),
    ("VL", ["faculty"], "60.00", "VACATION_DAYS", False, False, False, "EL", "2.00"),
)


def create_policies(apps, schema_editor):
    LeavePolicy = apps.get_model("elm", "LeavePolicy")
    db = schema_editor.connection.alias
    for (code, kinds, entitlement, counting, carry, half, evidence,
         conversion_target, divisor) in POLICIES:
        LeavePolicy.objects.using(db).update_or_create(
            leave_type_code=code,
            defaults={
                "employee_kinds": kinds,
                "annual_entitlement": Decimal(entitlement),
                "day_counting": counting,
                "carries_forward": carry,
                "half_day_allowed": half,
                "requires_medical_evidence": evidence,
                "conversion_target_code": conversion_target,
                "conversion_divisor": Decimal(divisor),
                "is_active": True,
            },
        )


def remove_policies(apps, schema_editor):
    LeavePolicy = apps.get_model("elm", "LeavePolicy")
    LeavePolicy.objects.using(schema_editor.connection.alias).filter(
        leave_type_code__in=[row[0] for row in POLICIES]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("elm", "0002_leavepolicy_leavebalance_leavecalendar_and_more")]
    operations = [
        migrations.RunPython(create_policies, remove_policies),
    ]
