from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="RoleSlot",
            fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                    ("role", models.CharField(choices=[("caretaker", "Caretaker"), ("warden", "Warden")], max_length=16, unique=True))],
        ),
        migrations.CreateModel(
            name="Announcement",
            fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                    ("owner_role", models.CharField(choices=[("caretaker", "Caretaker"), ("warden", "Warden")], max_length=12)),
                    ("title", models.CharField(max_length=160)), ("body", models.TextField(max_length=4000)),
                    ("created_by_user_id", models.BigIntegerField()), ("created_at", models.DateTimeField(auto_now_add=True))],
        ),
        migrations.CreateModel(
            name="Feedback",
            fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                    ("user_id", models.BigIntegerField(db_index=True)), ("text", models.TextField(max_length=4000)),
                    ("created_at", models.DateTimeField(auto_now_add=True))],
        ),
        migrations.CreateModel(
            name="MenuItem",
            fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                    ("week_start", models.DateField(db_index=True)),
                    ("day", models.PositiveSmallIntegerField(choices=[(0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"), (4, "Friday"), (5, "Saturday"), (6, "Sunday")])),
                    ("meal", models.CharField(choices=[("breakfast", "Breakfast"), ("lunch", "Lunch"), ("dinner", "Dinner")], max_length=12)),
                    ("item", models.CharField(max_length=160)), ("updated_by_user_id", models.BigIntegerField()),
                    ("updated_at", models.DateTimeField(auto_now=True))],
        ),
        migrations.CreateModel(
            name="RebateRequest",
            fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                    ("user_id", models.BigIntegerField(db_index=True)),
                    ("reason", models.CharField(choices=[("medical", "Medical"), ("institute_leave", "Institute leave"), ("family_function", "Family function"), ("other", "Other")], max_length=24)),
                    ("explanation", models.CharField(blank=True, max_length=500)), ("start_date", models.DateField()),
                    ("end_date", models.DateField()), ("status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")], default="pending", max_length=12)),
                    ("submitted_at", models.DateTimeField(auto_now_add=True)), ("decided_at", models.DateTimeField(blank=True, null=True)),
                    ("decided_by_user_id", models.BigIntegerField(blank=True, null=True))],
            options={"indexes": [models.Index(fields=["user_id", "start_date", "end_date"], name="mms_rebate_overlap_idx")]},
        ),
        migrations.CreateModel(
            name="RegistrationWindow",
            fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                    ("cycle", models.CharField(max_length=80, unique=True)), ("opens_at", models.DateTimeField()),
                    ("closes_at", models.DateTimeField()), ("created_by_user_id", models.BigIntegerField())],
        ),
        migrations.CreateModel(
            name="RoleAssignment",
            fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                    ("role", models.CharField(choices=[("caretaker", "Caretaker"), ("warden", "Warden")], max_length=16)),
                    ("user_id", models.BigIntegerField(db_index=True)), ("starts_at", models.DateTimeField()),
                    ("ends_at", models.DateTimeField(blank=True, null=True)), ("recorded_by_user_id", models.BigIntegerField())],
            options={"indexes": [models.Index(fields=["role", "starts_at", "ends_at"], name="mms_role_active_idx")]},
        ),
        migrations.CreateModel(
            name="SpecialFoodRequest",
            fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                    ("user_id", models.BigIntegerField(db_index=True)), ("requested_date", models.DateField()),
                    ("description", models.CharField(max_length=500)), ("charge", models.DecimalField(blank=True, decimal_places=2, max_digits=9, null=True)),
                    ("status", models.CharField(choices=[("requested", "Requested"), ("approved", "Approved"), ("rejected", "Rejected"), ("served", "Served"), ("cancelled", "Cancelled")], default="requested", max_length=12)),
                    ("submitted_at", models.DateTimeField(auto_now_add=True)), ("decision_deadline", models.DateTimeField(blank=True, null=True)),
                    ("decided_at", models.DateTimeField(blank=True, null=True)), ("decided_by_user_id", models.BigIntegerField(blank=True, null=True))],
        ),
        migrations.CreateModel(
            name="StudentRegistration",
            fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                    ("user_id", models.BigIntegerField(db_index=True)), ("cycle", models.CharField(db_index=True, max_length=80)),
                    ("request_type", models.CharField(choices=[("register", "Register"), ("deregister", "Deregister")], max_length=16)),
                    ("status", models.CharField(choices=[("pending", "Pending"), ("registered", "Registered"), ("deregistered", "Deregistered"), ("rejected", "Rejected")], default="pending", max_length=16)),
                    ("submitted_at", models.DateTimeField(auto_now_add=True)), ("decided_at", models.DateTimeField(blank=True, null=True)),
                    ("effective_date", models.DateField(blank=True, null=True)), ("decided_by_user_id", models.BigIntegerField(blank=True, null=True))],
            options={"indexes": [models.Index(fields=["user_id", "cycle", "-submitted_at"], name="mms_reg_user_cycle_idx")]},
        ),
        migrations.CreateModel(
            name="VacationSurvey",
            fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                    ("title", models.CharField(max_length=160)), ("vacation_start", models.DateField()),
                    ("vacation_end", models.DateField()), ("response_deadline", models.DateTimeField()),
                    ("created_by_user_id", models.BigIntegerField()), ("created_at", models.DateTimeField(auto_now_add=True))],
        ),
        migrations.CreateModel(
            name="VacationResponse",
            fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                    ("user_id", models.BigIntegerField(db_index=True)), ("response", models.CharField(blank=True, choices=[("yes", "Yes"), ("no", "No")], max_length=3, null=True)),
                    ("responded_at", models.DateTimeField(blank=True, null=True)), ("defaulted", models.BooleanField(default=False)),
                    ("survey", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="responses", to="mms.vacationsurvey"))],
            options={"constraints": [models.UniqueConstraint(fields=("survey", "user_id"), name="mms_vacation_one_response")]},
        ),
        migrations.AddConstraint(model_name="roleassignment", constraint=models.CheckConstraint(condition=models.Q(("ends_at__isnull", True), ("ends_at__gt", models.F("starts_at")), _connector="OR"), name="mms_role_dates_valid")),
    ]
