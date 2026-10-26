from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("leave", "0002_spec_aligned_request_fields")]

    operations = [
        migrations.AddField(
            model_name="leaverequest", name="chargeable_days",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6),
        ),
        migrations.AddField(
            model_name="leaverequest", name="charge_by_year",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.CreateModel(
            name="LeaveCalendar",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                            serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=120)),
                ("status", models.CharField(choices=[("draft", "Draft"),
                    ("published", "Published"), ("replaced", "Replaced")],
                    default="draft", max_length=12)),
                ("created_by_user_id", models.IntegerField()),
                ("published_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"db_table": "leave_calendar"},
        ),
        migrations.CreateModel(
            name="LeaveBalance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                            serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("employee_user_id", models.IntegerField(db_index=True)),
                ("leave_type", models.CharField(choices=[("CL", "Casual Leave"),
                    ("RH", "Restricted Holiday"), ("SCL", "Special Casual Leave"),
                    ("EL", "Earned Leave"), ("COL", "Commuted Leave"),
                    ("VL", "Vacation Leave")], max_length=3)),
                ("year", models.PositiveSmallIntegerField()),
                ("available", models.DecimalField(decimal_places=2, max_digits=7)),
            ],
            options={"db_table": "leave_balance"},
        ),
        migrations.CreateModel(
            name="LeaveCalendarDay",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                            serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("is_closed", models.BooleanField(default=True)),
                ("is_restricted_holiday", models.BooleanField(default=False)),
                ("calendar", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name="days", to="leave.leavecalendar")),
            ],
            options={"db_table": "leave_calendar_day"},
        ),
        migrations.CreateModel(
            name="LeaveBalanceChange",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                            serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("adjustment", "Administrator adjustment"),
                    ("approved", "Approved request deduction")], max_length=16)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=7)),
                ("note", models.CharField(blank=True, max_length=300)),
                ("actor_user_id", models.IntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("balance", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                    related_name="changes", to="leave.leavebalance")),
                ("leave_request", models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="balance_changes", to="leave.leaverequest")),
            ],
            options={"db_table": "leave_balance_change", "ordering": ("-created_at",)},
        ),
        migrations.AddConstraint(
            model_name="leavecalendar",
            constraint=models.UniqueConstraint(condition=models.Q(("status", "published")),
                fields=("status",), name="leave_one_published_calendar"),
        ),
        migrations.AddConstraint(
            model_name="leavecalendarday",
            constraint=models.UniqueConstraint(fields=("calendar", "date"),
                name="leave_calendar_date_unique"),
        ),
        migrations.AddConstraint(
            model_name="leavebalance",
            constraint=models.UniqueConstraint(fields=("employee_user_id", "leave_type", "year"),
                name="leave_balance_employee_type_year_unique"),
        ),
    ]
