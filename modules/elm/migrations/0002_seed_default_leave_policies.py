from decimal import Decimal

from django.db import migrations


def seed_default_leave_policies(apps, schema_editor):
    LeavePolicy = apps.get_model("elm", "LeavePolicy")
    defaults = [
        ("CL", "8.00", "all", False, False, False),
        ("RH", "2.00", "all", False, False, False),
        ("SCL", "15.00", "all", False, False, False),
        ("EL", "30.00", "staff", True, True, False),
        ("COL", "20.00", "all", True, True, True),
        ("VL", "60.00", "faculty", False, True, False),
    ]
    for category, entitlement, scope, carry, continuous, medical in defaults:
        LeavePolicy.objects.update_or_create(
            category=category,
            defaults={
                "annual_entitlement": Decimal(entitlement),
                "employee_scope": scope,
                "carry_forward": carry,
                "continuous_counting": continuous,
                "medical_evidence_required": medical,
                "enabled": True,
            },
        )


def reverse_seed_default_leave_policies(apps, schema_editor):
    LeavePolicy = apps.get_model("elm", "LeavePolicy")
    LeavePolicy.objects.filter(category__in=("CL", "RH", "SCL", "EL", "COL", "VL")).delete()


class Migration(migrations.Migration):
    dependencies = [("elm", "0001_initial")]
    operations = [
        migrations.RunPython(seed_default_leave_policies, migrations.RunPython.noop),
    ]
