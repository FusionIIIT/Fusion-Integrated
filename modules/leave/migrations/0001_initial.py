from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="LeaveBalance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user_id", models.IntegerField(db_index=True)),
                ("year", models.PositiveSmallIntegerField(db_index=True, default=2026)),
                ("category", models.CharField(choices=[("CL", "Casual Leave"), ("RH", "Restricted Holiday"), ("SCL", "Special Casual Leave"), ("EL", "Earned Leave"), ("COL", "Commuted Leave"), ("VL", "Vacation Leave")], max_length=8)),
                ("credited", models.DecimalField(decimal_places=1, default=Decimal("0.0"), max_digits=5)),
                ("availed", models.DecimalField(decimal_places=1, default=Decimal("0.0"), max_digits=5)),
                ("balance", models.DecimalField(decimal_places=1, default=Decimal("0.0"), max_digits=5)),
                ("lapsed", models.DecimalField(decimal_places=1, default=Decimal("0.0"), max_digits=5)),
            ],
            options={
                "db_table": "leave_balance",
                "constraints": [
                    models.UniqueConstraint(fields=["user_id", "year", "category"], name="leave_balance_user_year_cat_uniq")
                ],
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
                ("is_restricted_holiday", models.BooleanField(default=False)),
                ("is_closed_holiday", models.BooleanField(default=False)),
                ("is_vacation_period", models.BooleanField(default=False)),
                ("year", models.PositiveSmallIntegerField(db_index=True)),
            ],
            options={
                "db_table": "leave_holiday_calendar",
                "indexes": [
                    models.Index(fields=["year", "is_restricted_holiday"], name="leave_cal_rh_idx"),
                    models.Index(fields=["year", "is_vacation_period"], name="leave_cal_vac_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="LeaveRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user_id", models.IntegerField(db_index=True)),
                ("category", models.CharField(choices=[("CL", "Casual Leave"), ("RH", "Restricted Holiday"), ("SCL", "Special Casual Leave"), ("EL", "Earned Leave"), ("COL", "Commuted Leave"), ("VL", "Vacation Leave")], max_length=8)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("half_day", models.CharField(choices=[("full", "Full Day"), ("first_half", "First Half"), ("second_half", "Second Half")], default="full", max_length=16)),
                ("requested_days", models.DecimalField(decimal_places=1, max_digits=4)),
                ("purpose", models.TextField()),
                ("status", models.CharField(db_index=True, default="draft", max_length=38)),
                ("station_leave", models.BooleanField(default=False)),
                ("station_start_date", models.DateField(blank=True, null=True)),
                ("station_end_date", models.DateField(blank=True, null=True)),
                ("station_address", models.CharField(blank=True, max_length=255)),
                ("station_contact", models.CharField(blank=True, max_length=32)),
                ("substitute_user_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("substitute_status", models.CharField(default="not_required", max_length=16)),
                ("substitute_remarks", models.CharField(blank=True, max_length=255)),
                ("unit_head_user_id", models.IntegerField(blank=True, null=True)),
                ("unit_head_decision", models.CharField(blank=True, max_length=20)),
                ("unit_head_remarks", models.TextField(blank=True)),
                ("sanctioning_authority_user_id", models.IntegerField(blank=True, null=True)),
                ("sanctioning_decision", models.CharField(blank=True, max_length=20)),
                ("sanctioning_remarks", models.TextField(blank=True)),
                ("parent_leave_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("actual_resumption_date", models.DateField(blank=True, null=True)),
                ("resumption_verified", models.BooleanField(default=False)),
                ("restored_days", models.DecimalField(decimal_places=1, default=Decimal("0.0"), max_digits=4)),
                ("is_offline", models.BooleanField(default=False)),
                ("offline_reference", models.CharField(blank=True, max_length=100)),
            ],
            options={
                "db_table": "leave_request",
                "indexes": [
                    models.Index(fields=["user_id", "status"], name="leave_req_user_status_idx"),
                    models.Index(fields=["start_date", "end_date"], name="leave_req_dates_idx"),
                ],
            },
        ),
    ]
