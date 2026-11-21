import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="BasicUser",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user_id", models.AutoField(primary_key=True, serialize=False)),
                ("institute_id", models.CharField(db_index=True, max_length=32, unique=True)),
                ("user_type", models.CharField(choices=[("student", "Student"), ("faculty", "Faculty"), ("staff", "Staff")], db_index=True, max_length=16)),
                ("email", models.EmailField(db_index=True, max_length=254, unique=True)),
                ("first_name", models.CharField(max_length=64)),
                ("last_name", models.CharField(max_length=64)),
                ("contact_number", models.CharField(blank=True, max_length=20)),
                ("department", models.CharField(blank=True, db_index=True, max_length=80)),
                ("programme", models.CharField(blank=True, max_length=40)),
                ("discipline", models.CharField(blank=True, db_index=True, max_length=40)),
                ("batch_year", models.PositiveSmallIntegerField(blank=True, db_index=True, null=True)),
                ("employee_id", models.CharField(blank=True, db_index=True, max_length=32)),
                ("date_of_joining", models.DateField(blank=True, null=True)),
                ("expected_completion_date", models.DateField(blank=True, null=True)),
                ("status", models.CharField(choices=[("active", "Active"), ("deactivated", "Deactivated"), ("archived", "Archived")], db_index=True, default="active", max_length=16)),
                ("dashboard_access_enabled", models.BooleanField(default=True)),
                ("deactivated_at", models.DateTimeField(blank=True, null=True)),
                ("deactivation_reason", models.TextField(blank=True)),
                ("archived_at", models.DateTimeField(blank=True, null=True)),
                ("archival_reason", models.TextField(blank=True)),
                ("reversible_until", models.DateTimeField(blank=True, null=True)),
                ("is_permanently_archived", models.BooleanField(default=False)),
                ("has_pending_transactions", models.BooleanField(default=False)),
            ],
            options={
                "db_table": "system_admin_basic_user",
            },
        ),
        migrations.CreateModel(
            name="RoleDefinition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(db_index=True, max_length=64, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("description", models.TextField(blank=True)),
                ("module_association", models.CharField(db_index=True, max_length=64)),
                ("department_association", models.CharField(blank=True, max_length=80)),
                ("allowed_user_types", models.JSONField(default=list)),
                ("is_singular", models.BooleanField(default=False)),
                ("default_validity_days", models.PositiveIntegerField(blank=True, null=True)),
                ("permissions", models.JSONField(default=list)),
                ("conflict_role_codes", models.JSONField(default=list)),
                ("is_system_role", models.BooleanField(default=False)),
            ],
            options={
                "db_table": "system_admin_role_definition",
                "ordering": ["module_association", "name"],
            },
        ),
        migrations.CreateModel(
            name="ArchivedRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.CharField(db_index=True, max_length=64)),
                ("identifier", models.CharField(db_index=True, max_length=128)),
                ("data_payload", models.JSONField(default=dict)),
                ("retention_until", models.DateField(db_index=True)),
                ("backup_reference", models.CharField(max_length=256)),
                ("archived_at", models.DateTimeField(auto_now_add=True)),
                ("archived_by_user_id", models.IntegerField()),
                ("reason", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("archived", "Archived"), ("restored", "Restored"), ("purge_requested", "Purge Requested"), ("purged", "Permanently Purged")], db_index=True, default="archived", max_length=20)),
            ],
            options={
                "db_table": "system_admin_archived_record",
            },
        ),
        migrations.CreateModel(
            name="PurgeRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("requested_by_user_id", models.IntegerField()),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("reason", models.TextField()),
                ("status", models.CharField(choices=[("pending_it_head", "Pending IT Head"), ("approved", "Approved"), ("rejected", "Rejected")], db_index=True, default="pending_it_head", max_length=20)),
                ("it_head_user_id", models.IntegerField(blank=True, null=True)),
                ("authorized_at", models.DateTimeField(blank=True, null=True)),
                ("rejection_reason", models.TextField(blank=True)),
                ("archived_record", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="purge_requests", to="system_admin.archivedrecord")),
            ],
            options={
                "db_table": "system_admin_purge_request",
            },
        ),
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("timestamp", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("actor_user_id", models.IntegerField(db_index=True)),
                ("actor_username", models.CharField(max_length=64)),
                ("action", models.CharField(db_index=True, max_length=80)),
                ("target_type", models.CharField(blank=True, max_length=64)),
                ("target_id", models.CharField(blank=True, max_length=64)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("result", models.CharField(choices=[("success", "Success"), ("failure", "Failure")], db_index=True, default="success", max_length=16)),
                ("reason", models.TextField(blank=True)),
                ("details", models.JSONField(blank=True, default=dict)),
            ],
            options={
                "db_table": "system_admin_audit_log",
                "ordering": ["-timestamp"],
            },
        ),
        migrations.CreateModel(
            name="SuperAdminSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user_id", models.IntegerField(db_index=True)),
                ("session_key", models.CharField(db_index=True, max_length=128, unique=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.CharField(blank=True, max_length=256)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_activity", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "db_table": "system_admin_session",
            },
        ),
        migrations.CreateModel(
            name="FailedLoginAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("username", models.CharField(db_index=True, max_length=64)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("attempted_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "db_table": "system_admin_failed_login",
                "ordering": ["-attempted_at"],
            },
        ),
        migrations.CreateModel(
            name="SystemConfiguration",
            fields=[
                ("key", models.CharField(max_length=64, primary_key=True, serialize=False)),
                ("value", models.JSONField()),
                ("description", models.CharField(blank=True, max_length=256)),
                ("updated_by_user_id", models.IntegerField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "system_admin_configuration",
            },
        ),
        migrations.CreateModel(
            name="BulkOperationLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("batch_id", models.CharField(db_index=True, max_length=64, unique=True)),
                ("operation_type", models.CharField(max_length=32)),
                ("total_records", models.PositiveIntegerField()),
                ("successful_records", models.PositiveIntegerField(default=0)),
                ("failed_records", models.PositiveIntegerField(default=0)),
                ("initiated_by_user_id", models.IntegerField()),
                ("summary", models.JSONField(default=dict)),
                ("detailed_log", models.JSONField(default=list)),
            ],
            options={
                "db_table": "system_admin_bulk_operation_log",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="RoleAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user_id", models.IntegerField(db_index=True)),
                ("start_date", models.DateField(db_index=True)),
                ("end_date", models.DateField(blank=True, db_index=True, null=True)),
                ("scope_type", models.CharField(default="institute", max_length=32)),
                ("scope_id", models.CharField(blank=True, max_length=64)),
                ("reason", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("scheduled", "Scheduled"), ("active", "Active"), ("expired", "Expired"), ("revoked", "Revoked"), ("reassigned", "Reassigned")], db_index=True, default="scheduled", max_length=16)),
                ("assigned_by_user_id", models.IntegerField()),
                ("assigned_at", models.DateTimeField(auto_now_add=True)),
                ("effective_revoked_at", models.DateTimeField(blank=True, null=True)),
                ("revocation_reason", models.TextField(blank=True)),
                ("pending_task_disposition", models.CharField(blank=True, choices=[("transfer", "Transfer"), ("close", "Close")], max_length=16)),
                ("previous_holder_audit_until", models.DateTimeField(blank=True, null=True)),
                ("previous_assignment", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reassigned_to", to="system_admin.roleassignment")),
                ("role", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="assignments", to="system_admin.roledefinition")),
            ],
            options={
                "db_table": "system_admin_role_assignment",
            },
        ),
        migrations.AddIndex(
            model_name="basicuser",
            index=models.Index(fields=["status", "user_type"], name="sa_user_status_type_idx"),
        ),
        migrations.AddIndex(
            model_name="basicuser",
            index=models.Index(fields=["department", "status"], name="sa_user_dept_status_idx"),
        ),
        migrations.AddConstraint(
            model_name="basicuser",
            constraint=models.CheckConstraint(condition=models.Q(("status__in", ["active", "deactivated", "archived"])), name="sa_user_status_valid"),
        ),
        migrations.AddIndex(
            model_name="archivedrecord",
            index=models.Index(fields=["category", "retention_until"], name="sa_archive_cat_ret_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["action", "-timestamp"], name="sa_audit_action_ts_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["actor_user_id", "-timestamp"], name="sa_audit_actor_ts_idx"),
        ),
        migrations.AddIndex(
            model_name="roleassignment",
            index=models.Index(fields=["user_id", "status"], name="sa_role_assign_user_st_idx"),
        ),
        migrations.AddIndex(
            model_name="roleassignment",
            index=models.Index(fields=["role", "scope_type", "scope_id", "status"], name="sa_role_assign_scope_st_idx"),
        ),
        migrations.AddIndex(
            model_name="roleassignment",
            index=models.Index(fields=["status", "end_date"], name="sa_role_assign_end_date_idx"),
        ),
    ]
