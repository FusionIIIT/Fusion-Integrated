# Generated initial migration for modules.leave

from decimal import Decimal
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ApprovingAuthority",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user_id", models.IntegerField(db_index=True, unique=True)),
                ("role", models.CharField(choices=[("HOD", "Head of Department"), ("Registrar", "Registrar"), ("Director", "Director")], max_length=40)),
                ("department", models.CharField(blank=True, max_length=80)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "db_table": "leave_approving_authority",
            },
        ),
        migrations.CreateModel(
            name="LeaveRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user_id", models.IntegerField(db_index=True)),
                ("leave_type", models.CharField(choices=[("casual", "Casual Leave"), ("restricted", "Restricted Holiday"), ("medical", "Medical Leave"), ("earned", "Earned Leave"), ("vacation", "Vacation Leave"), ("sabbatical", "Sabbatical Leave")], db_index=True, max_length=32)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("duration_days", models.DecimalField(decimal_places=1, max_digits=5)),
                ("justification", models.TextField()),
                ("status", models.CharField(choices=[("draft", "Draft"), ("pending_current_authority", "Pending Current Authority"), ("approved", "Approved"), ("rejected", "Rejected"), ("cancelled", "Cancelled")], db_index=True, default="pending_current_authority", max_length=40)),
                ("current_authority_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("current_authority_role", models.CharField(blank=True, max_length=40)),
                ("forward_count", models.PositiveSmallIntegerField(default=0)),
                ("cancellation_reason", models.TextField(blank=True)),
                ("submission_date", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "leave_request",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="LeaveBalance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user_id", models.IntegerField(db_index=True)),
                ("leave_type", models.CharField(choices=[("casual", "Casual Leave"), ("restricted", "Restricted Holiday"), ("medical", "Medical Leave"), ("earned", "Earned Leave"), ("vacation", "Vacation Leave"), ("sabbatical", "Sabbatical Leave")], db_index=True, max_length=32)),
                ("year", models.PositiveSmallIntegerField(db_index=True)),
                ("total_entitlement", models.DecimalField(decimal_places=1, default=Decimal("12.0"), max_digits=5)),
                ("consumed_days", models.DecimalField(decimal_places=1, default=Decimal("0.0"), max_digits=5)),
                ("available_balance", models.DecimalField(decimal_places=1, default=Decimal("12.0"), max_digits=5)),
            ],
            options={
                "db_table": "leave_balance",
                "ordering": ["year", "leave_type"],
                "unique_together": {("user_id", "leave_type", "year")},
            },
        ),
        migrations.CreateModel(
            name="ApprovalDecision",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("authority_id", models.IntegerField(db_index=True)),
                ("next_authority_id", models.IntegerField(blank=True, null=True)),
                ("outcome", models.CharField(choices=[("approved", "Approved"), ("rejected", "Rejected"), ("forwarded", "Forwarded")], max_length=32)),
                ("remarks", models.TextField(blank=True)),
                ("decided_at", models.DateTimeField(auto_now_add=True)),
                ("request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="decisions", to="leave.leaverequest")),
            ],
            options={
                "db_table": "leave_approval_decision",
                "ordering": ["-decided_at"],
            },
        ),
        migrations.AddIndex(
            model_name="leaverequest",
            index=models.Index(fields=["user_id", "status"], name="leave_req_user_st_idx"),
        ),
        migrations.AddIndex(
            model_name="leaverequest",
            index=models.Index(fields=["current_authority_id", "status"], name="leave_req_auth_st_idx"),
        ),
    ]
