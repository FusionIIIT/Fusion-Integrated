from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="LeaveRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user_id", models.IntegerField(db_index=True)),
                ("leave_type_code", models.CharField(choices=[("CL", "Casual Leave"), ("RH", "Restricted Holiday"), ("SCL", "Special Casual Leave"), ("EL", "Earned Leave"), ("COL", "Commuted Leave"), ("VL", "Vacation Leave")], max_length=3)),
                ("requested_start_date", models.DateField()),
                ("requested_end_date", models.DateField()),
                ("day_part", models.CharField(choices=[("FULL", "Full day"), ("FIRST_HALF", "First half"), ("SECOND_HALF", "Second half")], default="FULL", max_length=12)),
                ("total_days", models.DecimalField(decimal_places=2, max_digits=6)),
                ("status", models.CharField(choices=[("SUBMITTED", "Submitted"), ("PENDING_UNIT_HEAD", "Pending Unit Head"), ("PENDING_SANCTION", "Pending sanction"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("WITHDRAWN", "Withdrawn"), ("CANCELLED", "Cancelled")], default="SUBMITTED", max_length=24)),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("approved_by_user_id", models.IntegerField(blank=True, null=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("rejection_reason", models.TextField(blank=True, default="")),
            ],
            options={
                "verbose_name": "Leave Request",
                "verbose_name_plural": "Leave Requests",
            },
        ),
        migrations.AddIndex(
            model_name="leaverequest",
            index=models.Index(fields=["user_id", "status"], name="elm_user_status_idx"),
        ),
        migrations.AddIndex(
            model_name="leaverequest",
            index=models.Index(fields=["status", "requested_start_date"], name="elm_status_start_idx"),
        ),
    ]
