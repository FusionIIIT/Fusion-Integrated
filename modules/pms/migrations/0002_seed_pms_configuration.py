"""Seed the policy values the specifications state outright (M1, DEC-7).

Only three values are seeded, because only these three are fixed by the
specifications: the 15-business-day review window (BR-PMS-031), the 60-day
resubmission window (BR-PMS-035) and the 30/15/5-day alert offsets
(PMS-AFR-176..178). Thresholds, appeal periods, escalation chains and
maintenance schedules are deliberately left absent — PS §2.4 says PMS must
not define them, so a default would be an invented policy.
"""

from django.db import migrations

SEEDED = {
    "review_business_days": 15,
    "revision_days": 60,
    "alert_offsets": [30, 15, 5],
}


def seed(apps, schema_editor):
    Configuration = apps.get_model("pms", "PmsConfiguration")
    for key, value in SEEDED.items():
        Configuration.objects.update_or_create(
            key=key,
            defaults={"value": value, "description": f"Seeded by M1 for {key}."},
        )


def unseed(apps, schema_editor):
    Configuration = apps.get_model("pms", "PmsConfiguration")
    Configuration.objects.filter(key__in=list(SEEDED)).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("pms", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
