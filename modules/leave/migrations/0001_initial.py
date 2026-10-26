from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="LeaveRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("employee_user_id", models.IntegerField(db_index=True)),
                ("leave_type", models.CharField(choices=[("annual", "Annual"),
                    ("sick", "Sick"), ("personal", "Personal")], max_length=16)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("reason", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("pending", "Pending"),
                    ("approved", "Approved"), ("rejected", "Rejected"),
                    ("cancelled", "Cancelled")], default="pending", max_length=12)),
                ("reviewed_by_user_id", models.IntegerField(blank=True, null=True)),
                ("reviewer_comment", models.CharField(blank=True, max_length=500)),
            ],
            options={"db_table": "leave_request", "ordering": ("-created_at",),
                     "constraints": [models.CheckConstraint(
                         condition=models.Q(("end_date__gte", models.F("start_date"))),
                         name="leave_dates_ordered")]},
        ),
    ]
