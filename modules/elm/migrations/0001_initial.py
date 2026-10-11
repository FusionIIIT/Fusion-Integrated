# Initial database schema for the generated ELM domain models.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="LeaveType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=20, unique=True)),
                ("name", models.CharField(max_length=50)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"db_table": "elm_leave_type", "verbose_name": "Leave Type", "verbose_name_plural": "Leave Types"},
        ),
        migrations.CreateModel(
            name="LeaveRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("employee_user_id", models.IntegerField(db_index=True)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("reason", models.TextField(max_length=2000)),
                ("status", models.CharField(choices=[("DRAFT","DRAFT"),("PENDING_UNIT_HEAD","PENDING_UNIT_HEAD"),("PENDING_ESTABLISHMENT","PENDING_ESTABLISHMENT"),("PENDING_FINAL_SANCTION","PENDING_FINAL_SANCTION"),("APPROVED","APPROVED"),("REJECTED","REJECTED"),("WITHDRAWN","WITHDRAWN"),("CANCELLED","CANCELLED")], db_index=True, default="DRAFT", max_length=32)),
                ("leave_type", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="requests", to="elm.leavetype")),
            ],
            options={
                "db_table": "elm_leave_request",
                "indexes": [models.Index(fields=["employee_user_id", "-created_at"], name="employee_history"), models.Index(fields=["status", "-created_at"], name="status_history")],
                "constraints": [models.CheckConstraint(check=models.Q(start_date__lte=models.F("end_date")), name="valid_date_range")],
            },
        ),
        migrations.CreateModel(
            name="LeaveRequestTransition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("from_status", models.CharField(choices=[("DRAFT","DRAFT"),("PENDING_UNIT_HEAD","PENDING_UNIT_HEAD"),("PENDING_ESTABLISHMENT","PENDING_ESTABLISHMENT"),("PENDING_FINAL_SANCTION","PENDING_FINAL_SANCTION"),("APPROVED","APPROVED"),("REJECTED","REJECTED"),("WITHDRAWN","WITHDRAWN"),("CANCELLED","CANCELLED")], max_length=32)),
                ("to_status", models.CharField(choices=[("DRAFT","DRAFT"),("PENDING_UNIT_HEAD","PENDING_UNIT_HEAD"),("PENDING_ESTABLISHMENT","PENDING_ESTABLISHMENT"),("PENDING_FINAL_SANCTION","PENDING_FINAL_SANCTION"),("APPROVED","APPROVED"),("REJECTED","REJECTED"),("WITHDRAWN","WITHDRAWN"),("CANCELLED","CANCELLED")], max_length=32)),
                ("actor_user_id", models.IntegerField(blank=True, null=True)),
                ("reason", models.CharField(blank=True, max_length=300)),
                ("at", models.DateTimeField(auto_now_add=True)),
                ("leave_request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="transitions", to="elm.leaverequest")),
            ],
            options={"db_table": "elm_leave_request_transition", "indexes": [models.Index(fields=["leave_request", "-at"], name="leave_request_desc_at")]},
        ),
    ]
