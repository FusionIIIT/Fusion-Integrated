"""Initial migration for Employee Leave Management (ELM)."""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="LeaveRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("applicant_id", models.BigIntegerField(db_index=True)),
                ("category", models.CharField(choices=[("CL", "Casual Leave"), ("RH", "Restricted Holiday"), ("SCL", "Special Casual Leave"), ("EL", "Earned Leave"), ("VL", "Vacation Leave"), ("COL", "Commuted Leave")], max_length=10)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("duration_days", models.DecimalField(decimal_places=2, max_digits=5)),
                ("is_half_day", models.BooleanField(default=False)),
                ("half_day_type", models.CharField(blank=True, max_length=20, null=True)),
                ("reason", models.TextField()),
                ("is_station_leave", models.BooleanField(default=False)),
                ("station_address", models.TextField(blank=True, default="")),
                ("emergency_contact", models.CharField(blank=True, default="", max_length=50)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("AWAITING_SUBSTITUTE_RESPONSE", "Awaiting Substitute Response"), ("AWAITING_APPLICANT_ACTION", "Awaiting Applicant Action"), ("AWAITING_UNIT_HEAD_REVIEW", "Awaiting Unit Head Review"), ("AWAITING_ESTABLISHMENT_REVIEW", "Awaiting Establishment Review"), ("AWAITING_SANCTION_AUTHORITY_REVIEW", "Awaiting Sanction Authority Review"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("WITHDRAWN", "Withdrawn"), ("AWAITING_CANCELLATION_REVIEW", "Awaiting Cancellation Review"), ("CANCELLED", "Cancelled"), ("AWAITING_EXTENSION_REVIEW", "Awaiting Extension Review"), ("AWAITING_RESUMPTION_REVIEW", "Awaiting Resumption Review")], db_index=True, default="DRAFT", max_length=50)),
                ("unit_head_recommendation", models.CharField(blank=True, default="", max_length=30)),
                ("unit_head_remarks", models.TextField(blank=True, default="")),
                ("sanctioning_authority_remarks", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "elm_leave_request",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="LeaveAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("employee_id", models.BigIntegerField(db_index=True)),
                ("category", models.CharField(choices=[("CL", "Casual Leave"), ("RH", "Restricted Holiday"), ("SCL", "Special Casual Leave"), ("EL", "Earned Leave"), ("VL", "Vacation Leave"), ("COL", "Commuted Leave")], max_length=10)),
                ("year", models.IntegerField(db_index=True)),
                ("allotted", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ("used", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ("pending", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ("available", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
            ],
            options={
                "db_table": "elm_leave_account",
                "unique_together": {("employee_id", "category", "year")},
            },
        ),
        migrations.CreateModel(
            name="LeavePolicyConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=100, unique=True)),
                ("value", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, default="")),
            ],
            options={
                "db_table": "elm_policy_config",
            },
        ),
        migrations.CreateModel(
            name="HolidayCalendarEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.IntegerField(db_index=True)),
                ("date", models.DateField(db_index=True)),
                ("name", models.CharField(max_length=200)),
                ("is_rh", models.BooleanField(default=False)),
            ],
            options={
                "db_table": "elm_holiday_calendar",
                "unique_together": {("date", "is_rh")},
            },
        ),
        migrations.CreateModel(
            name="SubstituteAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("substitute_id", models.BigIntegerField(db_index=True)),
                ("status", models.CharField(default="PENDING", max_length=20)),
                ("remarks", models.TextField(blank=True, default="")),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                ("request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="substitute_assignments", to="elm.leaverequest")),
            ],
            options={
                "db_table": "elm_substitute_assignment",
            },
        ),
        migrations.CreateModel(
            name="LeaveTransaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("delta", models.DecimalField(decimal_places=2, max_digits=6)),
                ("transaction_type", models.CharField(max_length=50)),
                ("reference_id", models.CharField(blank=True, default="", max_length=100)),
                ("idempotency_key", models.CharField(blank=True, max_length=120, null=True, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("account", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="transactions", to="elm.leaveaccount")),
            ],
            options={
                "db_table": "elm_leave_transaction",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="LeaveResumptionRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("actual_resumption_date", models.DateField()),
                ("adjustment_days", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("resumption_type", models.CharField(max_length=20)),
                ("remarks", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("request", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="resumption_record", to="elm.leaverequest")),
            ],
            options={
                "db_table": "elm_resumption_record",
            },
        ),
    ]
