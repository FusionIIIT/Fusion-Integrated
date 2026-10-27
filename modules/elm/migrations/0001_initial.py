# Initial schema for the Employee Leave Management module.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="LeaveEmployeeState",
            fields=[("employee_id", models.IntegerField(primary_key=True, serialize=False))],
            options={"db_table": "elm_employee_state"},
        ),
        migrations.CreateModel(
            name="LeaveBalance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("employee_id", models.IntegerField(db_index=True)),
                ("category", models.CharField(choices=[("CL", "CL"), ("RH", "RH"), ("SCL", "SCL"), ("EL", "EL"), ("COL", "COL"), ("VL", "VL")], max_length=3)),
                ("year", models.PositiveSmallIntegerField()),
                ("allotted", models.DecimalField(decimal_places=1, default=0, max_digits=7)),
                ("reserved", models.DecimalField(decimal_places=1, default=0, max_digits=7)),
                ("used", models.DecimalField(decimal_places=1, default=0, max_digits=7)),
            ],
            options={"db_table": "elm_leave_balance",
                     "indexes": [models.Index(fields=["employee_id", "year"], name="elm_balance_employee_year_idx")],
                     "constraints": [
                         models.UniqueConstraint(fields=("employee_id", "category", "year"), name="elm_balance_employee_category_year_uniq"),
                         models.CheckConstraint(condition=models.Q(allotted__gte=0, reserved__gte=0, used__gte=0), name="elm_balance_values_nonnegative"),
                         models.CheckConstraint(condition=models.Q(used__lte=models.F("allotted") - models.F("reserved")), name="elm_balance_not_overallocated"),
                     ]},
        ),
        migrations.CreateModel(
            name="HolidayCalendar",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=120)),
                ("is_effective", models.BooleanField(default=False)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"db_table": "elm_holiday_calendar",
                     "constraints": [models.UniqueConstraint(condition=models.Q(is_effective=True), fields=("is_effective",), name="elm_one_effective_calendar")]},
        ),
        migrations.CreateModel(
            name="LeaveApplication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("employee_id", models.IntegerField(db_index=True)),
                ("category", models.CharField(choices=[("CL", "CL"), ("RH", "RH"), ("SCL", "SCL"), ("EL", "EL"), ("COL", "COL"), ("VL", "VL")], max_length=3)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("half_day", models.CharField(blank=True, choices=[("", "Full day"), ("first", "First half"), ("second", "Second half")], max_length=8)),
                ("chargeable_days", models.DecimalField(decimal_places=1, max_digits=7)),
                ("reason", models.CharField(max_length=2000)),
                ("station_leave", models.BooleanField(default=False)),
                ("station_details", models.CharField(blank=True, max_length=500)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("withdrawn", "Withdrawn")], default="pending", max_length=12)),
                ("current_step_order", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("current_stage", models.CharField(blank=True, choices=[("", "Complete"), ("unit_head", "unit_head"), ("establishment", "establishment"), ("final", "final"), ("director_self", "director_self")], max_length=24)),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"db_table": "elm_leave_application",
                     "indexes": [
                         models.Index(fields=["employee_id", "-created_at"], name="elm_application_employee_idx"),
                         models.Index(fields=["status", "current_stage", "created_at"], name="elm_application_queue_idx"),
                         models.Index(fields=["start_date", "end_date", "status"], name="elm_application_overlap_idx"),
                     ],
                     "constraints": [
                         models.CheckConstraint(condition=models.Q(end_date__gte=models.F("start_date")), name="elm_application_dates_ordered"),
                         models.CheckConstraint(condition=models.Q(chargeable_days__gt=0), name="elm_application_days_positive"),
                     ]},
        ),
        migrations.CreateModel(
            name="LeaveApprovalRoute",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("employee_id", models.IntegerField(db_index=True)),
                ("category", models.CharField(choices=[("CL", "CL"), ("RH", "RH"), ("SCL", "SCL"), ("EL", "EL"), ("COL", "COL"), ("VL", "VL")], max_length=3)),
                ("step_order", models.PositiveSmallIntegerField()),
                ("stage", models.CharField(choices=[("unit_head", "unit_head"), ("establishment", "establishment"), ("final", "final"), ("director_self", "director_self")], max_length=24)),
                ("approver_user_id", models.IntegerField(db_index=True)),
            ],
            options={"db_table": "elm_approval_route", "ordering": ("step_order",),
                     "indexes": [models.Index(fields=["approver_user_id", "employee_id", "category"], name="elm_route_approver_idx")],
                     "constraints": [models.UniqueConstraint(fields=("employee_id", "category", "step_order"), name="elm_route_employee_category_step_uniq")]},
        ),
        migrations.CreateModel(
            name="LeaveCharge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("days", models.DecimalField(decimal_places=1, max_digits=7)),
                ("application", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="charges", to="elm.leaveapplication")),
                ("balance", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="charges", to="elm.leavebalance")),
            ],
            options={"db_table": "elm_leave_charge",
                     "constraints": [models.UniqueConstraint(fields=("application", "balance"), name="elm_charge_application_balance_uniq")]},
        ),
        migrations.CreateModel(
            name="HolidayDate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("day", models.DateField()),
                ("name", models.CharField(max_length=160)),
                ("kind", models.CharField(choices=[("closed", "Closed holiday"), ("restricted", "Restricted holiday")], max_length=12)),
                ("calendar", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dates", to="elm.holidaycalendar")),
            ],
            options={"db_table": "elm_holiday_date",
                     "indexes": [models.Index(fields=["calendar", "day"], name="elm_calendar_day_idx")],
                     "constraints": [models.UniqueConstraint(fields=("calendar", "day", "kind"), name="elm_calendar_date_kind_uniq")]},
        ),
        migrations.CreateModel(
            name="LeaveApplicationTransition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("from_status", models.CharField(max_length=12)),
                ("to_status", models.CharField(max_length=12)),
                ("from_stage", models.CharField(blank=True, max_length=24)),
                ("to_stage", models.CharField(blank=True, max_length=24)),
                ("actor_user_id", models.IntegerField(blank=True, null=True)),
                ("action", models.CharField(max_length=24)),
                ("note", models.CharField(blank=True, max_length=2000)),
                ("at", models.DateTimeField(auto_now_add=True)),
                ("application", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="transitions", to="elm.leaveapplication")),
            ],
            options={"db_table": "elm_application_transition", "ordering": ("at", "id")},
        ),
    ]
