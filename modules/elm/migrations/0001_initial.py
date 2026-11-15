import uuid
from decimal import Decimal
import django.utils.timezone
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="LeaveRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("applicant_user_id", models.CharField(db_index=True, max_length=64)),
                ("leave_type", models.CharField(choices=[("CL", "Casual Leave"), ("RH", "Restricted Holiday"), ("SCL", "Special Casual Leave"), ("EL", "Earned Leave"), ("COL", "Commuted Leave"), ("VL", "Vacation Leave")], max_length=8)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("duration_days", models.DecimalField(decimal_places=1, max_digits=4)),
                ("is_half_day", models.BooleanField(default=False)),
                ("half_day_session", models.CharField(blank=True, default="", max_length=4)),
                ("reason", models.TextField()),
                ("station_leave", models.BooleanField(default=False)),
                ("station_leave_address", models.TextField(blank=True, default="")),
                ("out_of_station_from", models.DateField(blank=True, null=True)),
                ("out_of_station_to", models.DateField(blank=True, null=True)),
                ("substitute_user_id", models.CharField(blank=True, db_index=True, default="", max_length=64)),
                ("substitute_status", models.CharField(choices=[("NOT_REQUIRED", "Not Required"), ("PENDING", "Pending Response"), ("ACCEPTED", "Accepted"), ("REJECTED", "Declined")], default="NOT_REQUIRED", max_length=16)),
                ("substitute_remarks", models.TextField(blank=True, default="")),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("PENDING_SUBSTITUTE", "Pending Substitute Acceptance"), ("PENDING_UNIT_HEAD", "Pending Unit Head Recommendation"), ("PENDING_AUTHORITY", "Pending Sanctioning Authority"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("WITHDRAWN", "Withdrawn by Applicant"), ("CANCELLED", "Cancelled")], db_index=True, default="DRAFT", max_length=32)),
                ("current_approver_role", models.CharField(blank=True, default="unit_head", max_length=64)),
                ("rejection_reason", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "elm_leave_request",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="LeaveBalance",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("user_id", models.CharField(db_index=True, max_length=64)),
                ("leave_type", models.CharField(choices=[("CL", "Casual Leave"), ("RH", "Restricted Holiday"), ("SCL", "Special Casual Leave"), ("EL", "Earned Leave"), ("COL", "Commuted Leave"), ("VL", "Vacation Leave")], max_length=8)),
                ("year", models.PositiveSmallIntegerField(default=2026)),
                ("credited", models.DecimalField(decimal_places=1, default=Decimal("0.0"), max_digits=5)),
                ("availed", models.DecimalField(decimal_places=1, default=Decimal("0.0"), max_digits=5)),
                ("pending", models.DecimalField(decimal_places=1, default=Decimal("0.0"), max_digits=5)),
            ],
            options={
                "db_table": "elm_leave_balance",
                "unique_together": {("user_id", "leave_type", "year")},
            },
        ),
        migrations.CreateModel(
            name="LeaveActionLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("actor_user_id", models.CharField(max_length=64)),
                ("actor_role", models.CharField(max_length=64)),
                ("action", models.CharField(max_length=32)),
                ("remarks", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("leave_request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="action_logs", to="elm.leaverequest")),
            ],
            options={
                "db_table": "elm_action_log",
                "ordering": ["created_at"],
            },
        ),
    ]
