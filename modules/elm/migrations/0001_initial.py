import django.utils.timezone
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="LeaveBalance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("employee_id", models.CharField(db_index=True, max_length=64)),
                ("is_faculty", models.BooleanField(default=False)),
                ("year", models.PositiveIntegerField()),
                (
                    "leave_type",
                    models.CharField(
                        choices=[
                            ("CL", "Casual Leave"),
                            ("RH", "Restricted Holiday"),
                            ("SCL", "Special Casual Leave"),
                            ("EL", "Earned Leave"),
                            ("VL", "Vacation Leave (Faculty)"),
                            ("COL", "Commuted Leave"),
                        ],
                        max_length=10,
                    ),
                ),
                ("total_allocated", models.DecimalField(decimal_places=1, default=0.0, max_digits=5)),
                ("carried_forward", models.DecimalField(decimal_places=1, default=0.0, max_digits=5)),
                ("used_days", models.DecimalField(decimal_places=1, default=0.0, max_digits=5)),
                ("lapsed_days", models.DecimalField(decimal_places=1, default=0.0, max_digits=5)),
                ("converted_days", models.DecimalField(decimal_places=1, default=0.0, max_digits=5)),
            ],
            options={
                "db_table": "elm_leave_balance",
                "ordering": ["year", "leave_type"],
                "unique_together": {("employee_id", "year", "leave_type")},
            },
        ),
        migrations.CreateModel(
            name="LeaveApplication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("applicant_id", models.CharField(db_index=True, max_length=64)),
                ("is_faculty", models.BooleanField(default=False)),
                ("is_director", models.BooleanField(default=False)),
                (
                    "leave_type",
                    models.CharField(
                        choices=[
                            ("CL", "Casual Leave"),
                            ("RH", "Restricted Holiday"),
                            ("SCL", "Special Casual Leave"),
                            ("EL", "Earned Leave"),
                            ("VL", "Vacation Leave (Faculty)"),
                            ("COL", "Commuted Leave"),
                        ],
                        max_length=10,
                    ),
                ),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("total_days", models.DecimalField(decimal_places=1, max_digits=5)),
                ("is_half_day", models.BooleanField(default=False)),
                ("reason", models.TextField()),
                ("requires_station_leave", models.BooleanField(default=False)),
                ("station_leave_address", models.TextField(blank=True, default="")),
                ("station_departure_datetime", models.DateTimeField(blank=True, null=True)),
                ("station_arrival_datetime", models.DateTimeField(blank=True, null=True)),
                ("substitute_id", models.CharField(blank=True, default="", max_length=64)),
                (
                    "substitute_status",
                    models.CharField(
                        choices=[("NONE", "None"), ("PENDING", "Pending"), ("ACCEPTED", "Accepted"), ("DECLINED", "Declined")],
                        default="NONE",
                        max_length=20,
                    ),
                ),
                ("substitute_remarks", models.TextField(blank=True, default="")),
                ("substitute_responded_at", models.DateTimeField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("DRAFT", "Draft"),
                            ("AWAITING_SUBSTITUTE", "Awaiting Substitute Response"),
                            ("SUBSTITUTE_DECLINED", "Substitute Declined"),
                            ("AWAITING_UNIT_HEAD", "Awaiting Unit Head Review"),
                            ("AWAITING_SANCTION", "Awaiting Final Sanction"),
                            ("AWAITING_DIRECTOR_SELF_SANCTION", "Awaiting Director Self-Sanction"),
                            ("APPROVED", "Approved"),
                            ("REJECTED", "Rejected"),
                            ("WITHDRAWN", "Withdrawn"),
                            ("AWAITING_CANCELLATION", "Awaiting Cancellation Review"),
                            ("CANCELLED", "Cancelled"),
                            ("AWAITING_RESUMPTION_VERIFICATION", "Awaiting Resumption Verification"),
                            ("CLOSED", "Resumed / Closed"),
                        ],
                        db_index=True,
                        default="DRAFT",
                        max_length=35,
                    ),
                ),
                ("unit_head_id", models.CharField(blank=True, default="", max_length=64)),
                (
                    "unit_head_recommendation",
                    models.CharField(
                        choices=[("NONE", "None"), ("RECOMMENDED", "Recommended"), ("REJECTED", "Rejected"), ("APPROVED_FINAL", "Approved Final")],
                        default="NONE",
                        max_length=20,
                    ),
                ),
                ("unit_head_remarks", models.TextField(blank=True, default="")),
                ("unit_head_reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("sanctioner_id", models.CharField(blank=True, default="", max_length=64)),
                (
                    "sanction_decision",
                    models.CharField(
                        choices=[("NONE", "None"), ("APPROVED", "Approved"), ("REJECTED", "Rejected")],
                        default="NONE",
                        max_length=20,
                    ),
                ),
                ("sanction_remarks", models.TextField(blank=True, default="")),
                ("sanctioned_at", models.DateTimeField(blank=True, null=True)),
                ("is_extension", models.BooleanField(default=False)),
                ("actual_resumption_date", models.DateField(blank=True, null=True)),
                ("actual_days_availed", models.DecimalField(blank=True, decimal_places=1, max_digits=5, null=True)),
                ("resumption_verified_by", models.CharField(blank=True, default="", max_length=64)),
                ("resumption_verified_at", models.DateTimeField(blank=True, null=True)),
                ("is_offline_record", models.BooleanField(default=False)),
                ("offline_sanction_ref", models.CharField(blank=True, default="", max_length=128)),
                ("offline_sanction_date", models.DateField(blank=True, null=True)),
                ("last_actionable_task_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("sla_reminder_sent", models.BooleanField(default=False)),
                ("sla_escalation_sent", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "parent_leave",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="extensions",
                        to="elm.leaveapplication",
                    ),
                ),
            ],
            options={
                "db_table": "elm_leave_application",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="LeaveHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("actor_id", models.CharField(max_length=64)),
                ("from_status", models.CharField(max_length=35)),
                ("to_status", models.CharField(max_length=35)),
                ("action", models.CharField(max_length=64)),
                ("remarks", models.TextField(blank=True, default="")),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                (
                    "application",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="history",
                        to="elm.leaveapplication",
                    ),
                ),
            ],
            options={
                "db_table": "elm_leave_history",
                "ordering": ["timestamp"],
            },
        ),
    ]
