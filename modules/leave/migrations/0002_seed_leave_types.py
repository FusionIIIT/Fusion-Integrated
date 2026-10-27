from django.db import migrations


LEAVE_TYPES = [
    ("CL", "Casual Leave"),
    ("RH", "Restricted Holiday"),
    ("SCL", "Special Casual Leave"),
    ("EL", "Earned Leave"),
    ("COL", "Commuted Leave; eligibility and medical requirements apply"),
    ("VL", "Vacation Leave"),
]


def seed_leave_types(apps, schema_editor):
    LeaveType = apps.get_model("leave", "LeaveType")
    db = schema_editor.connection.alias

    for code, description in LEAVE_TYPES:
        LeaveType.objects.using(db).get_or_create(
            name=code,
            defaults={"description": description},
        )


def remove_seeded_leave_types(apps, schema_editor):
    LeaveType = apps.get_model("leave", "LeaveType")
    db = schema_editor.connection.alias
    LeaveType.objects.using(db).filter(
        name__in=[code for code, _ in LEAVE_TYPES]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("leave", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            seed_leave_types,
            remove_seeded_leave_types,
        ),
    ]
