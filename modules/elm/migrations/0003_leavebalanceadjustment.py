import uuid

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("elm", "0002_workflow_status_and_current_leave_year")]

    operations = [
        migrations.CreateModel(
            name="LeaveBalanceAdjustment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("user_id", models.CharField(db_index=True, max_length=64)),
                ("leave_type", models.CharField(choices=[("CL", "Casual Leave"), ("RH", "Restricted Holiday"), ("SCL", "Special Casual Leave"), ("EL", "Earned Leave"), ("COL", "Commuted Leave"), ("VL", "Vacation Leave")], max_length=8)),
                ("year", models.PositiveSmallIntegerField()),
                ("actor_user_id", models.CharField(max_length=64)),
                ("previous_credited", models.DecimalField(decimal_places=1, max_digits=5)),
                ("credited", models.DecimalField(decimal_places=1, max_digits=5)),
                ("reason", models.TextField()),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
                "db_table": "elm_balance_adjustment",
                "ordering": ["-created_at"],
            },
        ),
    ]
