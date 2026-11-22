# Generated migration for BADMS module

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="BackupRecord",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("backup_type", models.CharField(choices=[("MANUAL", "Manual On-Demand"), ("AUTOMATIC", "Scheduled Automatic"), ("SPECIAL", "Special Archival Snapshot")], default="MANUAL", max_length=20)),
                ("dataset_name", models.CharField(db_index=True, default="primary_db", max_length=100)),
                ("status", models.CharField(choices=[("IN_PROGRESS", "In Progress"), ("SUCCESS", "Success"), ("FAILED", "Failed")], db_index=True, default="IN_PROGRESS", max_length=20)),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("file_path", models.CharField(blank=True, max_length=500)),
                ("file_size_bytes", models.BigIntegerField(default=0)),
                ("checksum_sha256", models.CharField(blank=True, max_length=64)),
                ("triggered_by_user_id", models.CharField(db_index=True, max_length=64)),
                ("error_message", models.TextField(blank=True)),
                ("alert_sent", models.BooleanField(default=False)),
                ("escalated_to_director", models.BooleanField(default=False)),
            ],
            options={
                "db_table": "badms_backup_record",
                "ordering": ["-started_at"],
            },
        ),
        migrations.CreateModel(
            name="BackupSchedule",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=120)),
                ("scope", models.CharField(choices=[("GLOBAL", "Global Institution Schedule"), ("LOCAL", "Dataset-Specific Local Schedule")], db_index=True, default="LOCAL", max_length=20)),
                ("dataset_name", models.CharField(db_index=True, default="primary_db", max_length=100)),
                ("frequency", models.CharField(choices=[("HOURLY", "Hourly"), ("DAILY", "Daily"), ("WEEKLY", "Weekly"), ("MONTHLY", "Monthly")], default="DAILY", max_length=20)),
                ("scheduled_time", models.CharField(default="02:00", max_length=10)),
                ("day_of_week", models.IntegerField(blank=True, null=True)),
                ("classification_filter", models.CharField(default="ALL", max_length=20)),
                ("repository_path", models.CharField(default="/var/backups/fusion", max_length=500)),
                ("is_active", models.BooleanField(default=True)),
                ("created_by_user_id", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "badms_backup_schedule",
                "ordering": ["scope", "dataset_name"],
            },
        ),
        migrations.CreateModel(
            name="StorageQuota",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("user_id", models.CharField(db_index=True, max_length=64, unique=True)),
                ("department_id", models.CharField(db_index=True, max_length=64)),
                ("allocated_storage_mb", models.DecimalField(decimal_places=2, default=1024.0, max_digits=10)),
                ("used_storage_mb", models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ("threshold_percent", models.DecimalField(decimal_places=2, default=80.0, max_digits=5)),
                ("is_alerted", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "badms_storage_quota",
            },
        ),
        migrations.CreateModel(
            name="ArchivalRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("request_number", models.CharField(db_index=True, max_length=32, unique=True)),
                ("file_name", models.CharField(max_length=255)),
                ("file_type", models.CharField(default="DATA", max_length=50)),
                ("file_size_mb", models.DecimalField(decimal_places=2, default=10.0, max_digits=10)),
                ("attachment_ref", models.CharField(blank=True, max_length=500)),
                ("requester_user_id", models.CharField(db_index=True, max_length=64)),
                ("department_id", models.CharField(db_index=True, max_length=64)),
                ("owners", models.CharField(blank=True, max_length=255)),
                ("reason", models.TextField()),
                ("initial_classification", models.CharField(choices=[("ROUTINE", "Routine"), ("SENSITIVE", "Sensitive"), ("CRITICAL", "Critical"), ("ARCHIVAL", "Archival")], default="ROUTINE", max_length=20)),
                ("authoritative_classification", models.CharField(blank=True, choices=[("ROUTINE", "Routine"), ("SENSITIVE", "Sensitive"), ("CRITICAL", "Critical"), ("ARCHIVAL", "Archival")], max_length=20)),
                ("status", models.CharField(choices=[("SUBMITTED", "Submitted"), ("REJECTED", "Rejected by HoD"), ("HOD_APPROVED", "Approved by HoD"), ("CLASSIFIED_NON_SENSITIVE", "Classified Non-Sensitive / Policy Applied"), ("CLASSIFIED_SENSITIVE", "Classified Sensitive / Routed to IT Security"), ("SENSITIVE_ARCHIVE_ENCRYPTED", "Sensitive Archive Encrypted"), ("SPECIAL_ARCHIVED", "Special Archival Completed")], db_index=True, default="SUBMITTED", max_length=35)),
                ("hod_user_id", models.CharField(blank=True, max_length=64)),
                ("hod_decision_date", models.DateTimeField(blank=True, null=True)),
                ("hod_remarks", models.TextField(blank=True)),
                ("classified_by_user_id", models.CharField(blank=True, max_length=64)),
                ("classified_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "badms_archival_request",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="EncryptedArchive",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("archive_code", models.CharField(db_index=True, max_length=64, unique=True)),
                ("encryption_algorithm", models.CharField(default="AES-256", max_length=32)),
                ("encrypted_at_rest", models.BooleanField(default=True)),
                ("encrypted_in_transit", models.BooleanField(default=True)),
                ("configured_by_user_id", models.CharField(max_length=64)),
                ("archive_file_path", models.CharField(max_length=500)),
                ("checksum_sha256", models.CharField(max_length=64)),
                ("retention_years", models.IntegerField(default=10)),
                ("retention_expiry_date", models.DateField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("archival_request", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="encrypted_archive", to="badms.archivalrequest")),
            ],
            options={
                "db_table": "badms_encrypted_archive",
            },
        ),
        migrations.CreateModel(
            name="StorageExtensionRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("request_number", models.CharField(db_index=True, max_length=32, unique=True)),
                ("requester_user_id", models.CharField(db_index=True, max_length=64)),
                ("department_id", models.CharField(db_index=True, max_length=64)),
                ("requested_additional_mb", models.DecimalField(decimal_places=2, max_digits=10)),
                ("current_usage_mb", models.DecimalField(decimal_places=2, max_digits=10)),
                ("justification", models.TextField()),
                ("status", models.CharField(choices=[("SUBMITTED", "Submitted"), ("APPROVED", "Approved by HoD"), ("REJECTED", "Rejected by HoD")], db_index=True, default="SUBMITTED", max_length=20)),
                ("hod_user_id", models.CharField(blank=True, max_length=64)),
                ("hod_decision_date", models.DateTimeField(blank=True, null=True)),
                ("hod_remarks", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "badms_storage_extension_request",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="RestorationRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("request_number", models.CharField(db_index=True, max_length=32, unique=True)),
                ("requester_user_id", models.CharField(db_index=True, max_length=64)),
                ("department_id", models.CharField(db_index=True, max_length=64)),
                ("reason", models.TextField()),
                ("target_location", models.CharField(default="/restores/workspace", max_length=255)),
                ("classification_snapshot", models.CharField(max_length=20)),
                ("status", models.CharField(choices=[("STANDARD_PENDING", "Restoration Requested / Standard Path"), ("SENSITIVE_PENDING_APPROVAL", "Sensitive Restoration Pending Approval"), ("REJECTED", "Rejected by SysAdmin"), ("APPROVED_FOR_RESTORATION", "Approved for Restoration"), ("RESTORED", "Restored")], db_index=True, max_length=35)),
                ("approved_by_user_id", models.CharField(blank=True, max_length=64)),
                ("approval_date", models.DateTimeField(blank=True, null=True)),
                ("approval_remarks", models.TextField(blank=True)),
                ("restored_by_user_id", models.CharField(blank=True, max_length=64)),
                ("restored_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("archival_request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="restoration_requests", to="badms.archivalrequest")),
            ],
            options={
                "db_table": "badms_restoration_request",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("timestamp", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("actor_user_id", models.CharField(db_index=True, max_length=64)),
                ("actor_role", models.CharField(max_length=64)),
                ("department_id", models.CharField(blank=True, db_index=True, max_length=64)),
                ("event_type", models.CharField(db_index=True, max_length=64)),
                ("target_entity_type", models.CharField(max_length=64)),
                ("target_entity_id", models.CharField(max_length=64)),
                ("details", models.JSONField(default=dict)),
                ("ip_address", models.CharField(blank=True, max_length=45)),
            ],
            options={
                "db_table": "badms_audit_event",
                "ordering": ["-timestamp"],
            },
        ),
    ]
