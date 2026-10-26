from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="LeavePolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("year_label", models.CharField(max_length=20, unique=True)),
                ("cl_days", models.PositiveSmallIntegerField(default=8)),
                ("rh_days", models.PositiveSmallIntegerField(default=2)),
                ("scl_days", models.PositiveSmallIntegerField(default=15)),
                ("el_days_non_faculty", models.PositiveSmallIntegerField(default=30)),
                ("col_days_non_faculty", models.PositiveSmallIntegerField(default=20)),
                ("faculty_vl_to_el_ratio", models.CharField(default="2:1", max_length=10)),
                ("is_published", models.BooleanField(default=False)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "db_table": "leave_policy",
                "verbose_name_plural": "leave policies",
            },
        ),
        migrations.CreateModel(
            name="HolidayCalendar",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("date", models.DateField(unique=True)),
                ("name", models.CharField(max_length=120)),
                ("kind", models.CharField(choices=[("holiday", "Public Holiday"), ("restricted_holiday", "Restricted Holiday")], default="holiday", max_length=24)),
                ("is_published", models.BooleanField(default=True)),
            ],
            options={
                "db_table": "leave_holiday_calendar",
                "ordering": ["date"],
            },
        ),
        migrations.CreateModel(
            name="LeaveBalance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user_id", models.IntegerField(db_index=True)),
                ("category", models.CharField(choices=[("CL", "Casual Leave"), ("RH", "Restricted Holiday"), ("SCL", "Special Casual Leave"), ("EL", "Earned Leave"), ("COL", "Commuted Leave"), ("VL", "Vacation Leave")], max_length=8)),
                ("balance_days", models.DecimalField(decimal_places=2, default=0.0, max_digits=6)),
                ("year", models.CharField(default="2026", max_length=12)),
            ],
            options={
                "db_table": "leave_balance",
            },
        ),
        migrations.CreateModel(
            name="SlaConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("task_class", models.CharField(max_length=60, unique=True)),
                ("reminder_hours", models.PositiveIntegerField(default=48)),
                ("escalation_hours", models.PositiveIntegerField(default=96)),
            ],
            options={
                "db_table": "leave_sla_config",
            },
        ),
        migrations.CreateModel(
            name="LeaveApplication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user_id", models.IntegerField(db_index=True)),
                ("category", models.CharField(choices=[("CL", "Casual Leave"), ("RH", "Restricted Holiday"), ("SCL", "Special Casual Leave"), ("EL", "Earned Leave"), ("COL", "Commuted Leave"), ("VL", "Vacation Leave")], max_length=8)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("half_day", models.BooleanField(default=False)),
                ("half", models.CharField(blank=True, null=True, choices=[("first", "First Half"), ("second", "Second Half")], max_length=10)),
                ("station_leave", models.BooleanField(default=False)),
                ("station_start", models.DateField(blank=True, null=True)),
                ("station_end", models.DateField(blank=True, null=True)),
                ("reason", models.TextField()),
                ("status", models.CharField(choices=[("draft", "Draft"), ("pending", "Pending"), ("awaiting_substitute", "Awaiting Substitute Response"), ("unit_head_review", "Under Unit Head Review"), ("processing", "In Higher Processing"), ("sanctioned", "Sanctioned"), ("rejected", "Rejected"), ("withdrawn", "Withdrawn"), ("cancellation_pending", "Cancellation Pending"), ("cancelled", "Cancelled"), ("extension_pending", "Extension Pending")], default="pending", max_length=24)),
                ("substitute_user_id", models.IntegerField(blank=True, null=True)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                ("decided_by_user_id", models.IntegerField(blank=True, null=True)),
                ("unit_head_status", models.CharField(blank=True, choices=[("pending", "Pending"), ("recommended", "Recommended"), ("not_recommended", "Not Recommended"), ("approved", "Approved"), ("rejected", "Rejected")], max_length=20)),
                ("unit_head_decided_at", models.DateTimeField(blank=True, null=True)),
                ("final_authority_role", models.CharField(blank=True, max_length=60)),
                ("is_extension", models.BooleanField(default=False)),
                ("actual_resume_date", models.DateField(blank=True, null=True)),
                ("withdrawal_reason", models.CharField(blank=True, max_length=300)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("parent_application", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="extensions", to="leave.leaveapplication")),
            ],
            options={
                "db_table": "leave_application",
            },
        ),
        migrations.CreateModel(
            name="ApprovalStep",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("step_order", models.PositiveSmallIntegerField(default=1)),
                ("authority_role", models.CharField(max_length=60)),
                ("authority_user_id", models.IntegerField(blank=True, null=True)),
                ("decision", models.CharField(choices=[("pending", "Pending"), ("recommended", "Recommended"), ("not_recommended", "Not Recommended"), ("approved", "Approved"), ("rejected", "Rejected")], default="pending", max_length=20)),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                ("comment", models.CharField(blank=True, max_length=300)),
                ("application", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="approval_steps", to="leave.leaveapplication")),
            ],
            options={
                "db_table": "leave_approval_step",
                "ordering": ["step_order"],
            },
        ),
        migrations.CreateModel(
            name="SubstituteRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("nominee_user_id", models.IntegerField(db_index=True)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("accepted", "Accepted"), ("declined", "Declined")], default="pending", max_length=12)),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                ("application", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="substitute_requests", to="leave.leaveapplication")),
            ],
            options={
                "db_table": "leave_substitute_request",
            },
        ),
    ]
