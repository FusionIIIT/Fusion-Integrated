# Generated for the ELM pilot module.
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="Employee",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user_id", models.PositiveBigIntegerField(blank=True, null=True, unique=True)),
                ("name", models.CharField(max_length=100)),
                ("department", models.CharField(max_length=100)),
            ],
            options={"ordering": ("name", "id")},
        ),
        migrations.CreateModel(
            name="LeaveRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("canceled", "Canceled"), ("extended", "Extended"), ("resumed", "Resumed")], default="pending", max_length=20)),
                ("reason", models.TextField()),
                ("decision_note", models.TextField(blank=True, default="")),
                ("decided_by_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("employee", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="leave_requests", to="elm.employee")),
            ],
            options={
                "permissions": [
                    ("view_all_leave_requests", "Can view all employee leave requests"),
                    ("can_submit_leave", "Can submit leave"),
                    ("can_approve_leave", "Can approve leave"),
                    ("can_reject_leave", "Can reject leave"),
                    ("can_withdraw_leave", "Can withdraw leave"),
                    ("can_cancel_leave", "Can cancel leave"),
                    ("can_extend_leave", "Can extend leave"),
                    ("can_resume_leave", "Can resume leave"),
                    ("can_view_leave_history", "Can view leave history"),
                ],
                "ordering": ("-created_at", "-id"),
            },
        ),
        migrations.AddIndex(model_name="leaverequest", index=models.Index(fields=["employee", "status"], name="elm_emp_status_idx")),
        migrations.AddIndex(model_name="leaverequest", index=models.Index(fields=["start_date", "end_date"], name="elm_leave_dates_idx")),
    ]
