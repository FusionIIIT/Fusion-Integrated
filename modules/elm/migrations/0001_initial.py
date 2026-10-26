# Initial ELM MVP schema.
from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="LeaveApplication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                            serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user_id", models.IntegerField(db_index=True)),
                ("leave_type", models.CharField(choices=[
                    ("CL", "Casual Leave"),
                    ("RH", "Restricted Holiday"),
                    ("SCL", "Special Casual Leave"),
                    ("EL", "Earned Leave"),
                    ("COL", "Commuted Leave"),
                    ("VL", "Vacation Leave"),
                ], max_length=3)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("reason", models.TextField(max_length=2000)),
                ("status", models.CharField(choices=[
                    ("pending", "Pending"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                    ("withdrawn", "Withdrawn"),
                ], db_index=True, default="pending", max_length=12)),
            ],
            options={
                "db_table": "elm_leave_application",
                "ordering": ("-id",),
                "indexes": [
                    models.Index(fields=["user_id", "status"],
                                 name="elm_app_user_status_idx"),
                    models.Index(fields=["user_id", "-created_at"],
                                 name="elm_app_user_created_idx"),
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=Q(start_date__lte=F("end_date")),
                        name="elm_leave_dates_ordered",
                    ),
                ],
            },
        ),
    ]
