"""Seed the current leave-type policy, routing default, SLA thresholds and the
settings singleton, so a fresh database can process leave without an admin
visiting the policy screen first (BR-EL-002..BR-EL-009, BR-EL-032)."""
from decimal import Decimal

from django.db import migrations

TYPES = [
    ("CL", "Casual Leave", "any", "8", False, False, True, False, False, False,
     True, False),
    ("RH", "Restricted Holiday", "any", "2", False, False, False, False, False,
     False, True, False),
    ("SCL", "Special Casual Leave", "any", "15", False, False, False, False,
     False, False, False, False),
    ("EL", "Earned Leave", "any", "30", True, True, False, True, True, True,
     False, False),
    ("COL", "Commuted Leave", "any", "20", True, True, False, True, True, True,
     False, True),
    ("VL", "Vacation Leave", "faculty", "60", False, True, False, True, True,
     True, False, False),
]

SLA = [
    ("substitute", 48, 96, "Unit Head"),
    ("unit_head", 72, 144, "Registrar"),
    ("establishment", 48, 96, "Registrar"),
    ("final_sanction", 72, 144, "Director"),
    ("director_sanction", 48, 96, "Director"),
]


def seed(apps, schema_editor):
    LeaveTypeConfig = apps.get_model("elm", "LeaveTypeConfig")
    for (category, label, kind, entitlement, carry, continuous, half_day,
         substitute, resumption, extension, unit_final, medical) in TYPES:
        LeaveTypeConfig.objects.update_or_create(
            category=category,
            defaults=dict(
                label=label, employee_kind=kind,
                annual_entitlement=Decimal(entitlement), carry_forward=carry,
                continuous=continuous, half_day=half_day,
                requires_substitute=substitute, requires_resumption=resumption,
                allows_extension=extension, unit_head_final=unit_final,
                requires_medical_evidence=medical, active=True))

    HierarchyConfig = apps.get_model("elm", "HierarchyConfig")
    HierarchyConfig.objects.update_or_create(
        category="",
        defaults=dict(establishment_required=True,
                      final_authority_designation="Registrar"))

    SlaConfig = apps.get_model("elm", "SlaConfig")
    for task_type, reminder, escalation, designation in SLA:
        SlaConfig.objects.update_or_create(
            task_type=task_type,
            defaults=dict(reminder_hours=reminder, escalation_hours=escalation,
                          escalate_to_designation=designation, active=True))

    ElmSettings = apps.get_model("elm", "ElmSettings")
    ElmSettings.objects.get_or_create(pk=1)


def unseed(apps, schema_editor):
    apps.get_model("elm", "LeaveTypeConfig").objects.all().delete()
    apps.get_model("elm", "HierarchyConfig").objects.all().delete()
    apps.get_model("elm", "SlaConfig").objects.all().delete()
    apps.get_model("elm", "ElmSettings").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("elm", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
