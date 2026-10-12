from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="LeaveRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user_id", models.IntegerField(db_index=True)),
                ("leave_type", models.CharField(choices=[("CL", "Casual Leave"), ("RH", "Restricted Holiday"), ("SCL", "Special Casual Leave"), ("EL", "Earned Leave"), ("COL", "Compensatory Off Leave"), ("VL", "Vacation Leave")], max_length=8)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("days_requested", models.DecimalField(decimal_places=1, default=Decimal("1.0"), max_digits=4, validators=[django.core.validators.MinValueValidator(Decimal("0.5"))])),
                ("half_day", models.BooleanField(default=False)),
                ("reason", models.TextField(blank=True)),
                ("substitute_user_id", models.IntegerField(blank=True, null=True)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("cancelled", "Cancelled")], default="pending", max_length=16)),
                ("remarks", models.TextField(blank=True)),
            ],
            options={
                "db_table": "elm_leave_request",
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
                ("leave_type", models.CharField(max_length=8)),
                ("year", models.CharField(max_length=8)),
                ("entitled_days", models.DecimalField(decimal_places=1, default=0, max_digits=6)),
                ("used_days", models.DecimalField(decimal_places=1, default=0, max_digits=6)),
                ("remaining_days", models.DecimalField(decimal_places=1, default=0, max_digits=6)),
            ],
            options={
                "db_table": "elm_leave_balance",
                "unique_together": {("user_id", "leave_type", "year")},
            },
        ),
        migrations.CreateModel(
            name="LeaveEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("actor_user_id", models.IntegerField()),
                ("action", models.CharField(max_length=32)),
                ("note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="elm.leaverequest")),
            ],
            options={
                "db_table": "elm_leave_event",
                "ordering": ["-created_at"],
            },
        ),
    ]
