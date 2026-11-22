from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class BackupSchedule(TimeStampedModel):
    class Scope(models.TextChoices):
        LOCAL = "local", "Local"
        GLOBAL = "global", "Global"

    scope = models.CharField(max_length=8, choices=Scope.choices)
    dataset_key = models.CharField(max_length=120)
    cron_expression = models.CharField(max_length=100)
    timezone = models.CharField(max_length=64, default="UTC")
    classification_filters = models.JSONField(default=list, blank=True)
    enabled = models.BooleanField(default=True)
    changed_by_user_id = models.IntegerField()

    class Meta:
        db_table = "badms_backup_schedule"
        constraints = [
            models.UniqueConstraint(
                fields=["scope", "dataset_key"],
                name="badms_schedule_scope_dataset_uniq",
            ),
            models.CheckConstraint(
                condition=~Q(dataset_key=""),
                name="badms_schedule_dataset_nonempty",
            ),
        ]


class BackupRun(TimeStampedModel):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    class Trigger(models.TextChoices):
        MANUAL = "manual", "Manual"
        SCHEDULED = "scheduled", "Scheduled"

    dataset_key = models.CharField(max_length=120)
    trigger = models.CharField(max_length=12, choices=Trigger.choices)
    schedule = models.ForeignKey(
        BackupSchedule, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="runs",
    )
    started_by_user_id = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices,
                              default=Status.QUEUED)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    storage_key = models.CharField(max_length=500, blank=True)
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    error_code = models.CharField(max_length=80, blank=True)
    consecutive_failures = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "badms_backup_run"
        indexes = [
            models.Index(fields=["dataset_key", "created_at"],
                         name="badms_backup_dataset_idx"),
            models.Index(fields=["status", "created_at"],
                         name="badms_backup_status_idx"),
        ]


class ArchivalRequest(TimeStampedModel):
    class Classification(models.TextChoices):
        CRITICAL = "critical", "Critical"
        SENSITIVE = "sensitive", "Sensitive"
        ROUTINE = "routine", "Routine"
        ARCHIVAL = "archival", "Archival"

    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SECURITY_REVIEW = "security_review", "Security review"
        READY_TO_ARCHIVE = "ready_to_archive", "Ready to archive"
        CLASSIFIED = "classified", "Classified"
        ARCHIVED = "archived", "Archived"
        FAILED = "failed", "Failed"

    requester_user_id = models.IntegerField(db_index=True)
    department_code = models.CharField(max_length=80, blank=True, db_index=True)
    file_name = models.CharField(max_length=120)
    data_date = models.DateField()
    owners = models.CharField(max_length=500)
    file_type = models.CharField(max_length=80)
    reason = models.TextField(max_length=2000)
    attachment_key = models.CharField(max_length=500, blank=True)
    attachment_sha256 = models.CharField(max_length=64, blank=True)
    attachment_size_bytes = models.PositiveBigIntegerField(default=0)
    initial_classification = models.CharField(
        max_length=12, choices=Classification.choices,
        default=Classification.ROUTINE,
    )
    classification = models.CharField(
        max_length=12, choices=Classification.choices, blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.SUBMITTED)
    decision_by_user_id = models.IntegerField(null=True, blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)
    decision_reason = models.CharField(max_length=500, blank=True)
    special_operation = models.BooleanField(default=False)
    storage_key = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "badms_archival_request"
        indexes = [
            models.Index(fields=["requester_user_id", "created_at"],
                         name="badms_archive_requester_idx"),
            models.Index(fields=["department_code", "status"],
                         name="badms_archive_department_idx"),
        ]


class RestoreRequest(TimeStampedModel):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        RESTORING = "restoring", "Restoring"
        RESTORED = "restored", "Restored"
        FAILED = "failed", "Failed"

    archive = models.ForeignKey(ArchivalRequest, on_delete=models.PROTECT,
                                related_name="restore_requests")
    requester_user_id = models.IntegerField(db_index=True)
    reason = models.TextField(max_length=2000)
    status = models.CharField(max_length=12, choices=Status.choices,
                              default=Status.SUBMITTED)
    decision_by_user_id = models.IntegerField(null=True, blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=80, blank=True)

    class Meta:
        db_table = "badms_restore_request"
        indexes = [
            models.Index(fields=["requester_user_id", "created_at"],
                         name="badms_restore_requester_idx"),
        ]


class StorageExtensionRequest(TimeStampedModel):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    requester_user_id = models.IntegerField(db_index=True)
    department_code = models.CharField(max_length=80, blank=True, db_index=True)
    current_usage_bytes = models.PositiveBigIntegerField()
    quota_bytes = models.PositiveBigIntegerField()
    requested_bytes = models.PositiveBigIntegerField()
    justification = models.TextField(max_length=2000)
    status = models.CharField(max_length=12, choices=Status.choices,
                              default=Status.SUBMITTED)
    decision_by_user_id = models.IntegerField(null=True, blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)
    decision_reason = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "badms_storage_extension_request"
        indexes = [
            models.Index(fields=["department_code", "status"],
                         name="badms_extension_department_idx"),
        ]


class StorageObservation(models.Model):
    user_id = models.IntegerField(db_index=True)
    used_bytes = models.PositiveBigIntegerField()
    quota_bytes = models.PositiveBigIntegerField()
    observed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "badms_storage_observation"
        indexes = [
            models.Index(fields=["user_id", "-observed_at"],
                         name="badms_storage_user_date_idx"),
        ]

    def __str__(self):
        return f"Storage observation for user {self.user_id} at {self.observed_at}"


class SecurityPolicyVersion(models.Model):
    classification = models.CharField(
        max_length=12, choices=ArchivalRequest.Classification.choices,
    )
    effective_from = models.DateTimeField()
    retention_days = models.PositiveIntegerField(null=True, blank=True)
    encryption_required = models.BooleanField(default=False)
    created_by_user_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "badms_security_policy_version"
        constraints = [
            models.UniqueConstraint(
                fields=["classification", "effective_from"],
                name="badms_policy_class_effective_uniq",
            ),
        ]
        ordering = ["classification", "-effective_from"]

    def __str__(self):
        return f"{self.classification} policy effective {self.effective_from}"


class AuditEvent(models.Model):
    actor_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    action = models.CharField(max_length=80)
    resource = models.CharField(max_length=40)
    resource_id = models.CharField(max_length=80, blank=True)
    outcome = models.CharField(max_length=16)
    details = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "badms_audit_event"
        indexes = [
            models.Index(fields=["resource", "resource_id", "occurred_at"],
                         name="badms_audit_resource_idx"),
            models.Index(fields=["actor_user_id", "occurred_at"],
                         name="badms_audit_actor_idx"),
        ]

    def __str__(self):
        return f"{self.action} {self.resource} {self.resource_id}".strip()

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("BADMS audit events are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("BADMS audit events are append-only.")


class NotificationOutbox(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENDING = "sending", "Sending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    recipient_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    recipient_email = models.EmailField(blank=True)
    subject = models.CharField(max_length=200)
    body = models.TextField(max_length=4000)
    status = models.CharField(max_length=8, choices=Status.choices,
                              default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField()
    claimed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "badms_notification_outbox"
        indexes = [
            models.Index(fields=["status", "next_attempt_at"],
                         name="badms_notify_pending_idx"),
        ]

    def __str__(self):
        return f"{self.status} notification {self.pk}"
