from django.db import migrations, models


def seed_categories(apps, schema_editor):
    LeaveCategory = apps.get_model("elm", "LeaveCategory")
    categories = [
        ("CL", "Casual Leave", 8, False, False),
        ("RH", "Restricted Holiday", 2, False, False),
        ("SCL", "Special Casual Leave", 15, False, False),
        ("EL", "Earned Leave", 30, True, True),
        ("COL", "Commuted Leave", 20, True, True),
        ("VL", "Vacation Leave", 60, False, True),
    ]
    for code, label, entitlement, carry_forward, continuous in categories:
        LeaveCategory.objects.get_or_create(
            code=code,
            defaults={
                "label": label,
                "entitlement_days": entitlement,
                "carry_forward": carry_forward,
                "continuous_counting": continuous,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("elm", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="leaveapplication",
            name="station_leave_details",
            field=models.TextField(
                blank=True,
                help_text="Travel/location details required when Station Leave applies",
            ),
        ),
        migrations.RunPython(seed_categories, migrations.RunPython.noop),
    ]
