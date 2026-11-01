from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="ArchiveRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("requester_id", models.IntegerField(db_index=True)),
                ("department", models.CharField(blank=True, db_index=True, max_length=120)),
                ("file_name", models.CharField(max_length=255)),
                ("data_date", models.DateField()),
                ("owners", models.CharField(max_length=500)),
                ("file_type", models.CharField(max_length=80)),
                ("reason", models.TextField()),
                ("attachment", models.FileField(upload_to="badms/archives/requests/")),
                ("initial_classification", models.CharField(choices=[("ROUTINE", "Routine"), ("CRITICAL", "Critical"), ("SENSITIVE", "Sensitive"), ("ARCHIVAL", "Archival")], default="ROUTINE", max_length=12)),
                ("classification", models.CharField(choices=[("ROUTINE", "Routine"), ("CRITICAL", "Critical"), ("SENSITIVE", "Sensitive"), ("ARCHIVAL", "Archival")], default="ROUTINE", max_length=12)),
                ("status", models.CharField(choices=[("SUBMITTED", "Submitted"), ("HOD_APPROVED", "HoD approved"), ("HOD_REJECTED", "HoD rejected"), ("CLASSIFIED", "Classified"), ("SECURITY_REVIEW", "Security review"), ("ARCHIVED", "Archived")], default="SUBMITTED", max_length=20)),
                ("decision_note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "badms_archive_request", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("actor_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("action", models.CharField(db_index=True, max_length=120)),
                ("object_type", models.CharField(blank=True, max_length=60)),
                ("object_id", models.CharField(blank=True, max_length=80)),
                ("outcome", models.CharField(default="SUCCESS", max_length=20)),
                ("details", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={"db_table": "badms_audit_event", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="BackupRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_by", models.IntegerField(blank=True, db_index=True, null=True)),
                ("trigger", models.CharField(choices=[("MANUAL", "Manual"), ("SCHEDULED", "Scheduled")], default="MANUAL", max_length=12)),
                ("status", models.CharField(choices=[("RUNNING", "Running"), ("SUCCESS", "Success"), ("FAILED", "Failed")], default="RUNNING", max_length=12)),
                ("artifact", models.FileField(blank=True, upload_to="badms/backups/")),
                ("checksum", models.CharField(blank=True, max_length=64)),
                ("size_bytes", models.PositiveBigIntegerField(default=0)),
                ("message", models.TextField(blank=True)),
                ("started_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"db_table": "badms_backup_run", "ordering": ["-started_at"]},
        ),
    ]
