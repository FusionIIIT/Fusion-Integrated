from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="UserAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user_id", models.IntegerField(db_index=True, unique=True)),
                ("institute_id", models.CharField(db_index=True, max_length=50, unique=True)),
                ("email", models.EmailField(db_index=True, max_length=254, unique=True)),
                ("first_name", models.CharField(max_length=100)),
                ("last_name", models.CharField(max_length=100)),
                (
                    "user_type",
                    models.CharField(
                        choices=[("STUDENT", "Student"), ("FACULTY", "Faculty"), ("STAFF", "Staff")],
                        default="STUDENT",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ACTIVE", "Active"),
                            ("DEACTIVATED", "Deactivated"),
                            ("ARCHIVED_REVERSIBLE", "Archived (Reversible)"),
                            ("ARCHIVED_PERMANENT", "Archived (Permanently Non-Restorable)"),
                        ],
                        db_index=True,
                        default="ACTIVE",
                        max_length=30,
                    ),
                ),
                ("deactivated_at", models.DateTimeField(blank=True, null=True)),
                ("archived_at", models.DateTimeField(blank=True, null=True)),
                ("reversible_until", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "superadmin_user_account", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="RoleAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user_id", models.IntegerField(db_index=True)),
                ("role_code", models.CharField(db_index=True, max_length=100)),
                ("role_name", models.CharField(max_length=150)),
                ("scope", models.CharField(default="INSTITUTE", max_length=100)),
                ("is_singular", models.BooleanField(default=False)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("ACTIVE", "Active"), ("REVOKED", "Revoked"), ("EXPIRED", "Expired")],
                        default="ACTIVE",
                        max_length=20,
                    ),
                ),
                ("revocation_reason", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "superadmin_role_assignment"},
        ),
        migrations.CreateModel(
            name="AuditEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("timestamp", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("actor_username", models.CharField(db_index=True, max_length=150)),
                ("action", models.CharField(db_index=True, max_length=100)),
                ("target_id", models.CharField(blank=True, default="", max_length=100)),
                ("result", models.CharField(default="SUCCESS", max_length=20)),
                ("reason", models.TextField(blank=True, default="")),
            ],
            options={"db_table": "superadmin_audit_entry", "ordering": ["-timestamp"]},
        ),
    ]
