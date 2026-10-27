# Generated manually for the initial Leave foundation.
from django.db import migrations, models
from django.db.models import Q


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
                ("user_id", models.IntegerField(db_index=True)),
                ("category", models.CharField(choices=[("cl", "Casual Leave"),
                    ("rh", "Restricted Holiday")], max_length=2)),
                ("starts_on", models.DateField()),
                ("ends_on", models.DateField()),
                ("cl_half", models.CharField(choices=[("full", "Full day"),
                    ("first", "First half"), ("second", "Second half")],
                    default="full", max_length=6)),
                ("reason", models.CharField(max_length=500)),
                ("station_leave", models.BooleanField(default=False)),
                ("station_leave_details", models.CharField(blank=True, max_length=500)),
                ("status", models.CharField(choices=[("pending", "Pending"),
                    ("withdrawn", "Withdrawn")], default="pending", max_length=12)),
                ("withdrawn_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "db_table": "leave_request",
                "ordering": ["-starts_on", "-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="leaverequest",
            index=models.Index(fields=["user_id", "status", "starts_on"],
                               name="leave_reque_user_id_1bdb3e_idx"),
        ),
        migrations.AddConstraint(
            model_name="leaverequest",
            constraint=models.CheckConstraint(
                condition=Q(("ends_on__gte", models.F("starts_on"))),
                name="leave_request_valid_date_range"),
        ),
        migrations.AddConstraint(
            model_name="leaverequest",
            constraint=models.CheckConstraint(
                condition=Q(("category", "cl"), ("cl_half", "full"), _connector="OR"),
                name="leave_request_half_only_for_cl"),
        ),
    ]
