from django.db import migrations, models
import django.db.models.deletion


def seed_initial_leave_types(apps, schema_editor):
    LeaveType = apps.get_model("leave", "LeaveType")
    initial_types = [
        {"code": "CL", "name": "Casual Leave", "max_days_per_year": 8.0, "carry_forward": False, "requires_substitute": False},
        {"code": "RH", "name": "Restricted Holiday", "max_days_per_year": 2.0, "carry_forward": False, "requires_substitute": False},
        {"code": "SCL", "name": "Special Casual Leave", "max_days_per_year": 15.0, "carry_forward": False, "requires_substitute": True},
        {"code": "EL", "name": "Earned Leave", "max_days_per_year": 30.0, "carry_forward": True, "requires_substitute": True},
        {"code": "COL", "name": "Commuted / Caregiver Leave", "max_days_per_year": 20.0, "carry_forward": True, "requires_substitute": True},
        {"code": "VL", "name": "Vacation Leave", "max_days_per_year": 60.0, "carry_forward": False, "requires_substitute": False},
    ]
    for lt in initial_types:
        LeaveType.objects.get_or_create(code=lt["code"], defaults=lt)


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="LeaveType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(choices=[("CL", "Casual Leave"), ("RH", "Restricted Holiday"), ("SCL", "Special Casual Leave"), ("EL", "Earned Leave"), ("COL", "Commuted / Caregiver Leave"), ("VL", "Vacation Leave")], max_length=10, unique=True)),
                ("name", models.CharField(max_length=80)),
                ("max_days_per_year", models.DecimalField(decimal_places=1, default=0.0, max_digits=5)),
                ("carry_forward", models.BooleanField(default=False)),
                ("requires_substitute", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "db_table": "leave_type",
            },
        ),
        migrations.CreateModel(
            name="LeaveBalance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user_id", models.IntegerField(db_index=True)),
                ("year", models.PositiveIntegerField(default=2026)),
                ("allocated_days", models.DecimalField(decimal_places=1, default=0.0, max_digits=5)),
                ("used_days", models.DecimalField(decimal_places=1, default=0.0, max_digits=5)),
                ("leave_type", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="balances", to="leave.leavetype")),
            ],
            options={
                "db_table": "leave_balance",
            },
        ),
        migrations.CreateModel(
            name="LeaveRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user_id", models.IntegerField(db_index=True)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("duration_days", models.DecimalField(decimal_places=1, max_digits=5)),
                ("reason", models.TextField()),
                ("is_station_leave", models.BooleanField(default=False)),
                ("station_details", models.CharField(blank=True, default="", max_length=255)),
                ("status", models.CharField(choices=[("pending", "Pending Approval"), ("approved", "Approved"), ("rejected", "Rejected"), ("cancelled", "Cancelled")], default="pending", max_length=20)),
                ("approver_user_id", models.IntegerField(blank=True, null=True)),
                ("rejection_reason", models.CharField(blank=True, default="", max_length=255)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("leave_type", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="requests", to="leave.leavetype")),
            ],
            options={
                "db_table": "leave_request",
            },
        ),
        migrations.AddIndex(
            model_name="leaverequest",
            index=models.Index(fields=["user_id", "status"], name="leave_req_user_idx"),
        ),
        migrations.AddIndex(
            model_name="leaverequest",
            index=models.Index(fields=["approver_user_id", "status"], name="leave_req_approver_idx"),
        ),
        migrations.AddConstraint(
            model_name="leavebalance",
            constraint=models.UniqueConstraint(fields=("user_id", "leave_type", "year"), name="unique_user_leave_balance_year"),
        ),
        migrations.RunPython(seed_initial_leave_types, migrations.RunPython.noop),
    ]
