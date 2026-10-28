"""Initial schema for Employee Leave Management (ELM).

Hand-authored to match models.py exactly, because the pilot laptops had no
runnable Django/uv environment to run `makemigrations` on. Verified with
`python -m py_compile` and a field-by-field review against the models.
"""
import decimal

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="LeavePolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.CharField(
                    choices=[("CL", "Casual Leave"), ("RH", "Restricted Holiday"),
                             ("SCL", "Special Casual Leave"), ("EL", "Earned Leave"),
                             ("COL", "Commuted Leave"), ("VL", "Vacation Leave")],
                    max_length=8, unique=True)),
                ("annual_entitlement", models.DecimalField(
                    decimal_places=2, max_digits=5)),
                ("carries_forward", models.BooleanField(default=False)),
                ("continuous_counting", models.BooleanField(default=False)),
                ("half_day_allowed", models.BooleanField(default=False)),
                ("final_authority", models.CharField(default="unit_head",
                                                     max_length=24)),
            ],
            options={
                "verbose_name_plural": "leave policies",
                "db_table": "leave_policy",
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("annual_entitlement__gte", 0)),
                        name="leave_policy_entitlement_nonneg"),
                ],
            },
        ),
        migrations.CreateModel(
            name="Holiday",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("on_date", models.DateField(unique=True)),
                ("name", models.CharField(max_length=120)),
                ("kind", models.CharField(
                    choices=[("closed", "Closed holiday"),
                             ("restricted", "Restricted holiday")],
                    default="closed", max_length=12)),
                ("published", models.BooleanField(default=False)),
            ],
            options={"db_table": "leave_holiday", "ordering": ["on_date"]},
        ),
        migrations.CreateModel(
            name="VacationPeriod",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("label", models.CharField(max_length=120)),
                ("starts_on", models.DateField()),
                ("ends_on", models.DateField()),
            ],
            options={
                "db_table": "leave_vacation_period",
                "ordering": ["starts_on"],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("ends_on__gte", models.F("starts_on"))),
                        name="leave_vacation_period_valid"),
                ],
            },
        ),
        migrations.CreateModel(
            name="LeaveAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name="ID")),
                ("user_id", models.IntegerField(db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.CharField(
                    choices=[("CL", "Casual Leave"), ("RH", "Restricted Holiday"),
                             ("SCL", "Special Casual Leave"), ("EL", "Earned Leave"),
                             ("COL", "Commuted Leave"), ("VL", "Vacation Leave")],
                    max_length=8)),
                ("year", models.PositiveSmallIntegerField()),
                ("entitlement", models.DecimalField(
                    decimal_places=2, default=decimal.Decimal("0"), max_digits=6)),
                ("carried_forward", models.DecimalField(
                    decimal_places=2, default=decimal.Decimal("0"), max_digits=6)),
                ("availed", models.DecimalField(
                    decimal_places=2, default=decimal.Decimal("0"), max_digits=6)),
            ],
            options={
                "db_table": "leave_account",
                "constraints": [
                    models.UniqueConstraint(
                        fields=["user_id", "category", "year"],
                        name="leave_account_unique"),
                ],
                "indexes": [
                    models.Index(fields=["user_id", "year"],
                                 name="leave_account_user_year_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="LeaveApplication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("applicant_user_id", models.IntegerField(db_index=True)),
                ("category", models.CharField(
                    choices=[("CL", "Casual Leave"), ("RH", "Restricted Holiday"),
                             ("SCL", "Special Casual Leave"), ("EL", "Earned Leave"),
                             ("COL", "Commuted Leave"), ("VL", "Vacation Leave")],
                    max_length=8)),
                ("starts_on", models.DateField()),
                ("ends_on", models.DateField()),
                ("half_day", models.CharField(
                    choices=[("none", "Full day"), ("first_half", "First half"),
                             ("second_half", "Second half")],
                    default="none", max_length=12)),
                ("purpose", models.TextField(blank=True, max_length=2000)),
                ("leave_days", models.DecimalField(decimal_places=2, max_digits=6)),
                ("status", models.CharField(
                    choices=[("pending", "Pending"), ("recommended", "Recommended"),
                             ("not_recommended", "Not recommended"),
                             ("sanctioned", "Sanctioned"), ("rejected", "Rejected"),
                             ("withdrawn", "Withdrawn"),
                             ("cancellation_pending", "Cancellation requested"),
                             ("cancelled", "Cancelled")],
                    default="pending", max_length=24)),
                ("unit_head_user_id", models.IntegerField(
                    blank=True, db_index=True, null=True)),
                ("sanction_authority_user_id", models.IntegerField(
                    blank=True, null=True)),
                ("station_leave", models.BooleanField(default=False)),
                ("station_leave_place", models.CharField(blank=True, max_length=160)),
                ("station_leave_reason", models.CharField(blank=True, max_length=300)),
                ("resumption_on", models.DateField(blank=True, null=True)),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                ("decision_note", models.CharField(blank=True, max_length=300)),
            ],
            options={
                "db_table": "leave_application",
                "ordering": ["-created_at"],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("ends_on__gte", models.F("starts_on"))),
                        name="leave_application_period_valid"),
                    models.CheckConstraint(
                        condition=models.Q(("leave_days__gt", 0)),
                        name="leave_application_days_positive"),
                    models.CheckConstraint(
                        condition=~models.Q(("station_leave", True))
                        | ~models.Q(("station_leave_place", "")),
                        name="leave_application_station_has_place"),
                ],
                "indexes": [
                    models.Index(fields=["applicant_user_id", "-created_at"],
                                 name="leave_applicant_recent_idx"),
                    models.Index(fields=["status", "starts_on"],
                                 name="leave_status_start_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="LeaveTransition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name="ID")),
                ("from_status", models.CharField(max_length=24)),
                ("to_status", models.CharField(max_length=24)),
                ("actor_user_id", models.IntegerField(blank=True, null=True)),
                ("actor_role", models.CharField(blank=True, max_length=24)),
                ("reason", models.CharField(blank=True, max_length=300)),
                ("at", models.DateTimeField(auto_now_add=True)),
                ("application", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="transitions",
                    to="leave.leaveapplication")),
            ],
            options={"db_table": "leave_transition", "ordering": ["at"]},
        ),
        migrations.CreateModel(
            name="SubstituteNomination",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("substitute_user_id", models.IntegerField(db_index=True)),
                ("status", models.CharField(
                    choices=[("nominated", "Nominated"), ("accepted", "Accepted"),
                             ("declined", "Declined")],
                    default="nominated", max_length=12)),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                ("application", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="substitutes",
                    to="leave.leaveapplication")),
            ],
            options={
                "db_table": "leave_substitute_nomination",
                "constraints": [
                    models.UniqueConstraint(
                        fields=["application", "substitute_user_id"],
                        name="leave_substitute_unique"),
                ],
            },
        ),
        migrations.CreateModel(
            name="LeaveTask",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assigned_user_id", models.IntegerField(db_index=True)),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("reminded_at", models.DateTimeField(blank=True, null=True)),
                ("escalated_at", models.DateTimeField(blank=True, null=True)),
                ("is_open", models.BooleanField(default=True)),
                ("application", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="tasks", to="leave.leaveapplication")),
            ],
            options={
                "db_table": "leave_task",
                "indexes": [
                    models.Index(fields=["is_open", "due_at"],
                                 name="leave_task_open_due_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="YearEndRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("year", models.PositiveSmallIntegerField(unique=True)),
                ("processed_accounts", models.PositiveIntegerField(default=0)),
                ("exceptions", models.JSONField(blank=True, default=list)),
                ("ran_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"db_table": "leave_year_end_run", "ordering": ["-year"]},
        ),
    ]
