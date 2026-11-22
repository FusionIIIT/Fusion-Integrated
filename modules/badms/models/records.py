from django.db import models


class BackupRun(models.Model):
    class Status(models.TextChoices):
        RUNNING = "RUNNING", "Running"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    class Trigger(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        SCHEDULED = "SCHEDULED", "Scheduled"

    created_by = models.IntegerField(null=True, blank=True, db_index=True)
    trigger = models.CharField(max_length=12, choices=Trigger.choices, default=Trigger.MANUAL)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RUNNING)
    artifact = models.FileField(upload_to="badms/backups/", blank=True)
    checksum = models.CharField(max_length=64, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    message = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        db_table = "badms_backup_run"


class ArchiveRequest(models.Model):
    class Classification(models.TextChoices):
        ROUTINE = "ROUTINE", "Routine"
        CRITICAL = "CRITICAL", "Critical"
        SENSITIVE = "SENSITIVE", "Sensitive"
        ARCHIVAL = "ARCHIVAL", "Archival"

    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        HOD_APPROVED = "HOD_APPROVED", "HoD approved"
        HOD_REJECTED = "HOD_REJECTED", "HoD rejected"
        CLASSIFIED = "CLASSIFIED", "Classified"
        SECURITY_REVIEW = "SECURITY_REVIEW", "Security review"
        ARCHIVED = "ARCHIVED", "Archived"

    requester_id = models.IntegerField(db_index=True)
    department = models.CharField(max_length=120, blank=True, db_index=True)
    file_name = models.CharField(max_length=255)
    data_date = models.DateField()
    owners = models.CharField(max_length=500)
    file_type = models.CharField(max_length=80)
    reason = models.TextField()
    attachment = models.FileField(upload_to="badms/archives/requests/")
    initial_classification = models.CharField(
        max_length=12, choices=Classification.choices, default=Classification.ROUTINE
    )
    classification = models.CharField(
        max_length=12, choices=Classification.choices, default=Classification.ROUTINE
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    decision_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        db_table = "badms_archive_request"


class AuditEvent(models.Model):
    actor_id = models.IntegerField(null=True, blank=True, db_index=True)
    action = models.CharField(max_length=120, db_index=True)
    object_type = models.CharField(max_length=60, blank=True)
    object_id = models.CharField(max_length=80, blank=True)
    outcome = models.CharField(max_length=20, default="SUCCESS")
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        db_table = "badms_audit_event"
