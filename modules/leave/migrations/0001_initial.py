# Initial schema for Employee Leave Management.
from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="HolidayCalendar",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=150)),
                ("date", models.DateField(db_index=True)),
                ("kind", models.CharField(choices=[("closed", "Closed Holiday"), ("restricted", "Restricted Holiday")], default="closed", max_length=15)),
                ("year", models.PositiveSmallIntegerField(db_index=True)),
                ("is_published", models.BooleanField(default=True)),
            ],
            options={"db_table": "leave_holiday_calendar", "ordering": ["date"]},
        ),
        migrations.CreateModel(
            name="LeaveApplication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("user_id", models.IntegerField(db_index=True)),
                ("category", models.CharField(choices=[("CL", "Casual Leave"), ("RH", "Restricted Holiday"), ("SCL", "Special Casual Leave"), ("EL", "Earned Leave"), ("VL", "Vacation Leave"), ("COL", "Commuted Leave")], max_length=10)),
                ("start_date", models.DateField()), ("end_date", models.DateField()),
                ("half_day_type", models.CharField(choices=[("full", "Full Day"), ("first_half", "First Half"), ("second_half", "Second Half")], default="full", max_length=15)),
                ("days_count", models.DecimalField(decimal_places=1, default=Decimal("1.0"), max_digits=5)),
                ("purpose", models.TextField()), ("address_during_leave", models.TextField(blank=True)),
                ("is_station_leave", models.BooleanField(default=False)),
                ("station_departure_date", models.DateField(blank=True, null=True)),
                ("station_arrival_date", models.DateField(blank=True, null=True)),
                ("station_destination", models.CharField(blank=True, max_length=255)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("substitute_pending", "Pending Substitute Consent"), ("under_review", "Under Review"), ("approved", "Approved"), ("rejected", "Rejected"), ("withdrawn", "Withdrawn"), ("cancel_requested", "Cancellation Requested"), ("cancelled", "Cancelled"), ("extension_requested", "Extension Requested"), ("resumption_submitted", "Resumption Submitted"), ("closed", "Closed")], default="substitute_pending", max_length=30)),
                ("unit_head_user_id", models.IntegerField(blank=True, null=True)),
                ("unit_head_recommended", models.BooleanField(blank=True, null=True)),
                ("unit_head_remarks", models.TextField(blank=True)), ("unit_head_reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("establishment_user_id", models.IntegerField(blank=True, null=True)), ("establishment_remarks", models.TextField(blank=True)),
                ("establishment_reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("sanctioning_authority_user_id", models.IntegerField(blank=True, null=True)),
                ("sanctioning_remarks", models.TextField(blank=True)), ("sanctioned_at", models.DateTimeField(blank=True, null=True)),
                ("cancellation_reason", models.TextField(blank=True)), ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("resumption_date", models.DateField(blank=True, null=True)),
                ("actual_days_count", models.DecimalField(blank=True, decimal_places=1, max_digits=5, null=True)),
                ("resumption_remarks", models.TextField(blank=True)), ("resumption_reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("is_offline_sanctioned", models.BooleanField(default=False)), ("offline_reference_no", models.CharField(blank=True, max_length=120)),
                ("offline_sanction_date", models.DateField(blank=True, null=True)),
                ("parent_leave", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="extensions", to="leave.leaveapplication")),
            ],
            options={"db_table": "leave_application", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="LeaveBalance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("user_id", models.IntegerField(db_index=True)), ("year", models.PositiveSmallIntegerField(db_index=True)),
                ("is_faculty", models.BooleanField(default=False)), ("year_end_processed", models.BooleanField(default=False)),
                ("cl_balance", models.DecimalField(decimal_places=1, default=Decimal("8.0"), max_digits=5)),
                ("rh_balance", models.DecimalField(decimal_places=1, default=Decimal("2.0"), max_digits=5)),
                ("scl_balance", models.DecimalField(decimal_places=1, default=Decimal("15.0"), max_digits=5)),
                ("el_balance", models.DecimalField(decimal_places=1, default=Decimal("30.0"), max_digits=5)),
                ("vl_balance", models.DecimalField(decimal_places=1, default=Decimal("60.0"), max_digits=5)),
                ("col_balance", models.DecimalField(decimal_places=1, default=Decimal("20.0"), max_digits=5)),
            ],
            options={"db_table": "leave_balance"},
        ),
        migrations.CreateModel(
            name="LeavePolicyConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("key", models.CharField(max_length=80, unique=True)), ("value", models.JSONField(default=dict)),
                ("description", models.CharField(blank=True, max_length=255)),
            ],
            options={"db_table": "leave_policy_config"},
        ),
        migrations.CreateModel(
            name="VacationPeriod",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=150)), ("start_date", models.DateField()), ("end_date", models.DateField()),
                ("year", models.PositiveSmallIntegerField(db_index=True)), ("is_active", models.BooleanField(default=True)),
            ],
            options={"db_table": "leave_vacation_period", "ordering": ["start_date"]},
        ),
        migrations.CreateModel(
            name="SubstituteRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("substitute_user_id", models.IntegerField(db_index=True)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("accepted", "Accepted"), ("declined", "Declined")], default="pending", max_length=20)),
                ("responsibilities", models.TextField(blank=True)), ("response_remarks", models.TextField(blank=True)),
                ("responded_at", models.DateTimeField(blank=True, null=True)), ("is_current", models.BooleanField(default=True)),
                ("application", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="substitute_requests", to="leave.leaveapplication")),
            ],
            options={"db_table": "leave_substitute_request", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="LeaveLedgerEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("user_id", models.IntegerField(db_index=True)), ("category", models.CharField(max_length=10)),
                ("entry_type", models.CharField(choices=[("credit", "Annual Credit"), ("debit", "Leave Availment"), ("reversal", "Cancellation Reversal"), ("conversion", "VL to EL Conversion"), ("lapse", "Year-End Lapse"), ("adjustment", "Resumption Adjustment")], max_length=20)),
                ("change_amount", models.DecimalField(decimal_places=1, max_digits=5)), ("balance_after", models.DecimalField(decimal_places=1, max_digits=5)),
                ("reference_id", models.IntegerField(blank=True, null=True)), ("remarks", models.TextField(blank=True)),
                ("balance", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ledger_entries", to="leave.leavebalance")),
            ],
            options={"db_table": "leave_ledger_entry", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="LeaveActionHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("actor_user_id", models.IntegerField(db_index=True)), ("actor_role", models.CharField(blank=True, max_length=60)),
                ("action", models.CharField(max_length=40)), ("remarks", models.TextField(blank=True)),
                ("application", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="actions", to="leave.leaveapplication")),
            ],
            options={"db_table": "leave_action_history", "ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="leavebalance",
            constraint=models.UniqueConstraint(fields=("user_id", "year"), name="leave_balance_unique_user_year"),
        ),
        migrations.AddIndex(model_name="leavebalance", index=models.Index(fields=["user_id", "year"], name="leave_balance_user_year_idx")),
        migrations.AddIndex(model_name="leaveapplication", index=models.Index(fields=["user_id", "status"], name="leave_app_user_status_idx")),
        migrations.AddIndex(model_name="leaveapplication", index=models.Index(fields=["start_date", "end_date"], name="leave_app_dates_idx")),
        migrations.AddIndex(model_name="leaveapplication", index=models.Index(fields=["status"], name="leave_app_status_idx")),
        migrations.AddIndex(model_name="substituterequest", index=models.Index(fields=["substitute_user_id", "status"], name="leave_sub_user_status_idx")),
    ]
