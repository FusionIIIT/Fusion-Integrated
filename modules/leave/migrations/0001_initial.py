from django.db import migrations, models
import django.db.models.deletion


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
                ("code", models.CharField(max_length=10, unique=True)),
                ("name", models.CharField(max_length=60)),
                ("max_days_per_year", models.PositiveSmallIntegerField(default=12)),
                ("requires_attachment", models.BooleanField(default=False)),
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
                ("status", models.CharField(choices=[("pending", "Pending Approval"), ("approved", "Approved"), ("rejected", "Rejected"), ("cancelled", "Cancelled")], default="pending", max_length=15)),
                ("approver_user_id", models.IntegerField(blank=True, null=True)),
                ("rejection_reason", models.CharField(blank=True, max_length=255)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("leave_type", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="requests", to="leave.leavetype")),
            ],
            options={
                "db_table": "leave_request",
            },
        ),
        migrations.AddIndex(
            model_name="leaverequest",
            index=models.Index(fields=["user_id", "status"], name="leave_req_user_status_idx"),
        ),
        migrations.AddIndex(
            model_name="leaverequest",
            index=models.Index(fields=["approver_user_id", "status"], name="leave_req_appr_status_idx"),
        ),
        migrations.AddConstraint(
            model_name="leavebalance",
            constraint=models.UniqueConstraint(fields=("user_id", "leave_type", "year"), name="unique_user_leave_balance_per_year"),
        ),
    ]
