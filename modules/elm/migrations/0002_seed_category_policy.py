"""Seed the baseline entitlements (BR-EL-002..009). Idempotent; empty table or not."""
from django.db import migrations

BASELINE = {"CL": 8, "RH": 2, "SCL": 15, "EL": 30, "COL": 20, "VL": 60}


def seed(apps, schema_editor):
    CategoryPolicy = apps.get_model("elm", "CategoryPolicy")
    for category, days in BASELINE.items():
        CategoryPolicy.objects.get_or_create(category=category,
                                             defaults={"annual_days": days})


class Migration(migrations.Migration):
    dependencies = [("elm", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
