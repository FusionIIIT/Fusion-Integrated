"""BADMS records contain metadata only; archive bytes live in private storage."""

from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class BackupSchedule(TimeStampedModel):
    scope = models.CharField(max_length=12, choices=(("local", "Local"),
                                                      ("global", "Global")))
    dataset = models.CharField(max_length=120)
    frequency = models.CharField(max_length=24)
    scheduled_time = models.TimeField()
    timezone = models.CharField(max_length=64)
    classifications = models.JSONField(default=list, blank=True)
    enabled = models.BooleanField(default=True)
    updated_by = models.IntegerField()

    class Meta:
        db_table = "badms_backup_schedule"
        constraints = [models.UniqueConstraint(
            fields=["scope", "dataset"], name="badms_schedule_scope_dataset_uniq")]


class BackupRun(TimeStampedModel):
    TRIGGER = (("manual", "Manual"), ("scheduled", "Scheduled"))
    STATUS = (("running", "Running"), ("success", "Success"), ("failure", "Failure"))

    trigger = models.CharField(max_length=12, choices=TRIGGER)
    status = models.CharField(max_length=12, choices=STATUS, default="running")
    dataset = models.CharField(max_length=120)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_email = models.EmailField(blank=True)
    started_at = models.DateTimeField()
    scheduled_for = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    artifact_key = models.CharField(max_length=500, blank=True)
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    outcome = models.TextField(blank=True)
    integrity_verified = models.BooleanField(default=False)

    class Meta:
        db_table = "badms_backup_run"
        indexes = [models.Index(fields=["dataset", "-started_at"],
                                name="badms_run_dataset_time_idx")]
        constraints = [models.UniqueConstraint(fields=["dataset", "scheduled_for"],
                                                name="badms_run_schedule_once_uniq")]


class ArchiveRequest(TimeStampedModel, UserScopedModel):
    CLASSIFICATION = tuple((v, v) for v in ("Critical", "Sensitive", "Routine", "Archival"))
    STATUS = tuple((v, v) for v in (
        "Submitted", "Rejected", "HoD Approved",
        "Classified Non-Sensitive / Policy Applied",
        "Classified Sensitive / Routed to IT Security", "Sensitive Archive Encrypted"))

    department = models.CharField(max_length=80)
    requester_email = models.EmailField(blank=True)
    file_name = models.CharField(max_length=255)
    file_date = models.DateField()
    owners = models.JSONField(default=list)
    file_type = models.CharField(max_length=80)
    reason = models.TextField()
    attachment_key = models.CharField(max_length=500)
    attachment_size_bytes = models.PositiveBigIntegerField(default=0)
    initial_classification = models.CharField(max_length=16, choices=CLASSIFICATION,
                                              default="Routine")
    classification = models.CharField(max_length=16, choices=CLASSIFICATION,
                                      blank=True)
    status = models.CharField(max_length=64, choices=STATUS, default="Submitted")
    decision_note = models.CharField(max_length=500, blank=True)
    decision_by = models.IntegerField(null=True, blank=True)
    classified_by = models.IntegerField(null=True, blank=True)
    archive_key = models.CharField(max_length=500, blank=True)
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    retention_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "badms_archive_request"
        indexes = [models.Index(fields=["department", "status"],
                                name="badms_archive_dept_status_idx"),
                   models.Index(fields=["user_id", "-created_at"],
                                name="badms_archive_user_time_idx")]


class StorageExtensionRequest(TimeStampedModel, UserScopedModel):
    STATUS = (("Submitted", "Submitted"), ("Rejected", "Rejected"),
              ("Approved", "Approved"))

    department = models.CharField(max_length=80)
    requester_email = models.EmailField(blank=True)
    requested_bytes = models.PositiveBigIntegerField()
    justification = models.TextField()
    attachment_key = models.CharField(max_length=500, blank=True)
    usage_bytes = models.PositiveBigIntegerField()
    available_bytes = models.PositiveBigIntegerField()
    status = models.CharField(max_length=12, choices=STATUS, default="Submitted")
    decision_note = models.CharField(max_length=500, blank=True)
    decision_by = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "badms_storage_extension_request"
        indexes = [models.Index(fields=["department", "status"],
                                name="badms_storage_dept_status_idx")]


class RestorationRequest(TimeStampedModel, UserScopedModel):
    STATUS = tuple((v, v) for v in (
        "Restoration Requested / Standard Path", "Sensitive Restoration Pending Approval",
        "Rejected", "Approved for Restoration", "Restored"))

    department = models.CharField(max_length=80)
    requester_email = models.EmailField(blank=True)
    archive_request = models.ForeignKey(ArchiveRequest, on_delete=models.PROTECT,
                                        related_name="restorations")
    classification = models.CharField(max_length=16, choices=ArchiveRequest.CLASSIFICATION)
    status = models.CharField(max_length=48, choices=STATUS)
    decision_by = models.IntegerField(null=True, blank=True)
    outcome = models.TextField(blank=True)
    restored_key = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "badms_restoration_request"
        indexes = [models.Index(fields=["user_id", "-created_at"],
                                name="badms_restore_user_time_idx")]


class AuditEvent(TimeStampedModel):
    actor_user_id = models.IntegerField(null=True, blank=True)
    department = models.CharField(max_length=80, blank=True)
    action = models.CharField(max_length=100)
    object_type = models.CharField(max_length=60)
    object_id = models.CharField(max_length=64)
    outcome = models.CharField(max_length=40)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "badms_audit_event"
        indexes = [models.Index(fields=["department", "-created_at"],
                                name="badms_audit_dept_time_idx")]


class StorageThreshold(TimeStampedModel):
    user_id = models.IntegerField(unique=True)
    department = models.CharField(max_length=80, blank=True)
    usage_bytes = models.PositiveBigIntegerField(default=0)
    quota_bytes = models.PositiveBigIntegerField()
    is_full = models.BooleanField(default=False)

    class Meta:
        db_table = "badms_storage_threshold"


class SecurityPolicy(TimeStampedModel):
    """Institute supplied retention values; encryption requirements are fixed."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    retention_days = models.JSONField(default=dict, blank=True)
    updated_by = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "badms_security_policy"


class SpecialArchiveOperation(TimeStampedModel):
    actor_user_id = models.IntegerField()
    offline_request_reference = models.CharField(max_length=160)
    research_description = models.TextField()
    archive_key = models.CharField(max_length=500)
    checksum_sha256 = models.CharField(max_length=64)
    outcome = models.CharField(max_length=40, default="Sensitive Archive Encrypted")

    class Meta:
        db_table = "badms_special_archive_operation"


class NotificationOutbox(TimeStampedModel):
    STATUS = (("pending", "Pending"), ("sent", "Sent"), ("failed", "Failed"))

    recipient = models.EmailField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "badms_notification_outbox"
        indexes = [models.Index(fields=["status", "created_at"],
                                name="badms_outbox_status_idx")]
