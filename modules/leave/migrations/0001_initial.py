"""Create leave types, yearly balances, and employee leave requests."""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="LeaveType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.SlugField(max_length=32, unique=True)),
                ("name", models.CharField(max_length=80)),
                ("annual_allowance", models.DecimalField(decimal_places=2, default=0,
                                                          max_digits=6)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"db_table": "leave_type", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="LeaveBalance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user_id", models.IntegerField(db_index=True)),
                ("year", models.PositiveSmallIntegerField()),
                ("allocated_days", models.DecimalField(decimal_places=2, max_digits=6)),
                ("carried_days", models.DecimalField(decimal_places=2, default=0,
                                                      max_digits=6)),
                ("leave_type", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                                  related_name="balances", to="leave.leavetype")),
            ],
            options={"db_table": "leave_balance"},
        ),
        migrations.CreateModel(
            name="LeaveRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user_id", models.IntegerField(db_index=True)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("days", models.PositiveSmallIntegerField()),
                ("reason", models.CharField(max_length=1000)),
                ("status", models.CharField(choices=[("pending", "Pending"),
                                                      ("approved", "Approved"),
                                                      ("rejected", "Rejected"),
                                                      ("cancelled", "Cancelled")],
                                             db_index=True, default="pending", max_length=12)),
                ("reviewed_by_user_id", models.IntegerField(blank=True, null=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("review_note", models.CharField(blank=True, max_length=500)),
                ("leave_type", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                                  related_name="requests", to="leave.leavetype")),
            ],
            options={"db_table": "leave_request", "ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="leavebalance",
            constraint=models.UniqueConstraint(fields=("user_id", "leave_type", "year"),
                                               name="leave_balance_user_type_year_uniq"),
        ),
        migrations.AddConstraint(
            model_name="leavebalance",
            constraint=models.CheckConstraint(condition=models.Q(("allocated_days__gte", 0),
                                                                  ("carried_days__gte", 0)),
                                              name="leave_balance_nonnegative"),
        ),
        migrations.AddConstraint(
            model_name="leaverequest",
            constraint=models.CheckConstraint(condition=models.Q(("end_date__gte",
                                                                  models.F("start_date"))),
                                              name="leave_request_date_order"),
        ),
        migrations.AddConstraint(
            model_name="leaverequest",
            constraint=models.CheckConstraint(condition=models.Q(("days__gt", 0)),
                                              name="leave_request_days_positive"),
        ),
        migrations.AddIndex(
            model_name="leaverequest",
            index=models.Index(fields=["user_id", "-created_at"],
                               name="leave_request_user_recent_idx"),
        ),
    ]
