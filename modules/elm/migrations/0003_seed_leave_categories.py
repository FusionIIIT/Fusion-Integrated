from decimal import Decimal

from django.db import migrations


CATEGORIES = (
    {
        "code": "CL",
        "label": "Casual Leave",
        "annual_entitlement": Decimal("8"),
        "carry_forward": False,
        "continuous_day_counting": False,
        "applicable_to": "B",
        "supports_half_day": True,
    },
    {
        "code": "RH",
        "label": "Restricted Holiday",
        "annual_entitlement": Decimal("2"),
        "carry_forward": False,
        "continuous_day_counting": False,
        "applicable_to": "B",
        "supports_half_day": False,
    },
    {
        "code": "SCL",
        "label": "Special Casual Leave",
        "annual_entitlement": Decimal("15"),
        "carry_forward": False,
        "continuous_day_counting": False,
        "applicable_to": "B",
        "supports_half_day": False,
    },
    {
        "code": "EL",
        "label": "Earned Leave",
        "annual_entitlement": Decimal("30"),
        "carry_forward": True,
        "continuous_day_counting": True,
        "applicable_to": "S",
        "supports_half_day": False,
    },
    {
        "code": "COL",
        "label": "Commuted Leave",
        "annual_entitlement": Decimal("20"),
        "carry_forward": True,
        "continuous_day_counting": True,
        "applicable_to": "B",
        "supports_half_day": False,
    },
    {
        "code": "VL",
        "label": "Vacation Leave",
        "annual_entitlement": Decimal("60"),
        "carry_forward": False,
        "continuous_day_counting": True,
        "applicable_to": "F",
        "supports_half_day": False,
    },
)


def seed_categories(apps, schema_editor):
    LeaveCategory = apps.get_model("elm", "LeaveCategory")
    for category in CATEGORIES:
        LeaveCategory.objects.using(schema_editor.connection.alias).update_or_create(
            code=category["code"],
            defaults=category,
        )


class Migration(migrations.Migration):
    dependencies = [("elm", "0002_alter_leavecategory_applicable_to")]

    operations = [
        migrations.RunPython(seed_categories, migrations.RunPython.noop),
    ]
