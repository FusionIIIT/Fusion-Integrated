from django.db import models
from django.utils import timezone
from core.db.mixins import TimeStampedModel, UserScopedModel


class ArchiveClassification(models.TextChoices):
    ROUTINE = "routine", "Routine"
    SENSITIVE = "sensitive", "Sensitive"
    CRITICAL = "critical", "Critical"
    ARCHIVAL = "archival", "Archival"


class ArchiveStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    REJECTED = "rejected", "Rejected"
    HOD_APPROVED = "hod_approved", "HoD Approved"
    POLICY_APPLIED = "policy_applied", "Policy Applied"
    ROUTED_TO_SECURITY = "routed_to_security", "Routed to IT Security"
    ENCRYPTION_CONFIGURED = "encryption_configured", "Encryption Configured"
    ENCRYPTED_ARCHIVE_CREATED = "encrypted_archive_created", "Encrypted Archive Created"


class UserStorageQuota(TimeStampedModel):
    """User storage allocation and utilization in bytes."""
    DEFAULT_QUOTA_BYTES = 1024 * 1024 * 1024  # 1 GB

    user_id = models.IntegerField(unique=True, db_index=True)
    department = models.CharField(max_length=100, blank=True)
    allocated_bytes = models.BigIntegerField(default=DEFAULT_QUOTA_BYTES)
    used_bytes = models.BigIntegerField(default=0)

    class Meta:
        db_table = "badms_user_storage_quota"

    @property
    def remaining_bytes(self) -> int:
        return max(0, self.allocated_bytes - self.used_bytes)

    def __str__(self) -> str:
        return f"User {self.user_id} ({self.department}): {self.used_bytes}/{self.allocated_bytes} bytes"


class ArchivalRequest(UserScopedModel, TimeStampedModel):
    """Submission and lifecycle of an archive request."""
    department = models.CharField(max_length=100, db_index=True)
    file_name = models.CharField(max_length=255)
    document_date = models.DateField()
    owners = models.JSONField(default=list, help_text="List of usernames or user IDs associated with this archive")
    file_type = models.CharField(max_length=50)
    file_size_bytes = models.BigIntegerField(default=0)
    attachment_path = models.CharField(max_length=500, blank=True)
    reason = models.TextField()

    # Classification lifecycle
    initial_classification = models.CharField(
        max_length=30,
        choices=ArchiveClassification.choices,
        default=ArchiveClassification.ROUTINE,
    )
    authoritative_classification = models.CharField(
        max_length=30,
        choices=ArchiveClassification.choices,
        null=True,
        blank=True,
    )

    # Status lifecycle
    status = models.CharField(
        max_length=40,
        choices=ArchiveStatus.choices,
        default=ArchiveStatus.SUBMITTED,
        db_index=True,
    )

    # Security & Integrity
    checksum = models.CharField(max_length=64, blank=True, help_text="SHA-256 digest")
    encryption_algorithm = models.CharField(max_length=50, blank=True)
    is_encrypted = models.BooleanField(default=False)

    # HoD Decision
    hod_user_id = models.IntegerField(null=True, blank=True)
    hod_comments = models.TextField(blank=True)
    hod_decided_at = models.DateTimeField(null=True, blank=True)

    # SysAdmin Decision
    sysadmin_user_id = models.IntegerField(null=True, blank=True)
    sysadmin_comments = models.TextField(blank=True)
    sysadmin_classified_at = models.DateTimeField(null=True, blank=True)

    # IT Security Configuration
    security_user_id = models.IntegerField(null=True, blank=True)
    security_configured_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "badms_archival_request"
        indexes = [
            models.Index(fields=["user_id", "status"], name="badms_arc_user_status_idx"),
            models.Index(fields=["department", "status"], name="badms_arc_dept_status_idx"),
        ]

    def __str__(self) -> str:
        return f"ArchiveRequest #{self.pk}: {self.file_name} ({self.status})"


class BadmsAuditLog(models.Model):
    """Immutable audit trail for all BADMS actions."""
    actor_user_id = models.IntegerField(db_index=True)
    actor_role = models.CharField(max_length=50, blank=True)
    action = models.CharField(max_length=100, db_index=True)
    target_type = models.CharField(max_length=50, db_index=True)
    target_id = models.CharField(max_length=100, db_index=True)
    outcome = models.CharField(max_length=20, default="success")
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "badms_audit_log"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Audit #{self.pk}: {self.actor_user_id} - {self.action} on {self.target_type}:{self.target_id} ({self.outcome})"


class BadmsNotification(models.Model):
    """Notification ledger for BADMS events."""
    user_id = models.IntegerField(db_index=True)
    recipient_role = models.CharField(max_length=50, blank=True)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, db_index=True)
    related_object_id = models.CharField(max_length=100, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "badms_notification"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Notification to {self.user_id} ({self.recipient_role}): {self.subject}"


class BackupType(models.TextChoices):
    FULL = "full", "Full"
    DIFFERENTIAL = "differential", "Differential"
    INCREMENTAL = "incremental", "Incremental"


class BackupScope(models.TextChoices):
    LOCAL = "local", "Local"
    GLOBAL = "global", "Global"
    DATASET = "dataset", "Dataset"


class BackupStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class BackupExecution(TimeStampedModel):
    """Record of a backup run, either manual or scheduled."""
    backup_type = models.CharField(max_length=20, choices=BackupType.choices, default=BackupType.FULL)
    scope = models.CharField(max_length=20, choices=BackupScope.choices, default=BackupScope.LOCAL)
    target_dataset = models.CharField(max_length=100, default="all")
    status = models.CharField(max_length=20, choices=BackupStatus.choices, default=BackupStatus.PENDING, db_index=True)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    size_bytes = models.BigIntegerField(default=0)
    checksum = models.CharField(max_length=64, blank=True, help_text="SHA-256 integrity hash")
    repository_reachable = models.BooleanField(default=True)
    integrity_verified = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    consecutive_failure_count = models.IntegerField(default=0)
    initiated_by_user_id = models.IntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict)

    class Meta:
        db_table = "badms_backup_execution"
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"Backup #{self.pk} ({self.scope}/{self.backup_type}): {self.status}"


class BackupFrequency(models.TextChoices):
    HOURLY = "hourly", "Hourly"
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"


class BackupSchedule(TimeStampedModel):
    """Configuration for automated backup schedules and policy enforcement."""
    name = models.CharField(max_length=150)
    schedule_type = models.CharField(max_length=20, choices=BackupScope.choices, default=BackupScope.LOCAL)
    target_dataset = models.CharField(max_length=100, default="all")
    frequency = models.CharField(max_length=20, choices=BackupFrequency.choices, default=BackupFrequency.DAILY)
    execution_time = models.TimeField(help_text="Time of day for execution (HH:MM:SS)")
    classification_filter = models.CharField(max_length=50, blank=True, default="all")
    is_active = models.BooleanField(default=True)
    repository_path = models.CharField(max_length=255, default="/var/backups/badms")
    created_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "badms_backup_schedule"
        ordering = ["schedule_type", "name"]

    def __str__(self) -> str:
        return f"Schedule '{self.name}' ({self.schedule_type}/{self.frequency} at {self.execution_time})"


class RestorationStatus(models.TextChoices):
    PENDING_APPROVAL = "pending_approval", "Pending Approval"
    APPROVED = "approved", "Approved"
    RESTORING = "restoring", "Restoring"
    COMPLETED = "completed", "Completed"
    REJECTED = "rejected", "Rejected"
    FAILED = "failed", "Failed"


class RestorationRequest(TimeStampedModel):
    """Workflow record for archive and backup restoration requests."""
    archive_id = models.IntegerField(null=True, blank=True, db_index=True)
    backup_id = models.IntegerField(null=True, blank=True, db_index=True)
    requester_user_id = models.IntegerField(db_index=True)
    target_type = models.CharField(max_length=50, default="archive")
    target_name = models.CharField(max_length=255)
    reason = models.TextField()
    target_destination = models.CharField(max_length=255, default="/restored")
    is_sensitive = models.BooleanField(default=False)
    status = models.CharField(
        max_length=30,
        choices=RestorationStatus.choices,
        default=RestorationStatus.COMPLETED,
        db_index=True,
    )
    approved_by_user_id = models.IntegerField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    restored_at = models.DateTimeField(null=True, blank=True)
    integrity_verified = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "badms_restoration_request"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Restoration #{self.pk} for '{self.target_name}' ({self.status})"


class StorageExtensionStatus(models.TextChoices):
    SUBMITTED = "submitted", "Submitted"
    HOD_APPROVED = "hod_approved", "HoD Approved"
    REJECTED = "rejected", "Rejected"


class StorageExtensionRequest(TimeStampedModel):
    """Workflow record for user storage quota extension requests."""
    user_id = models.IntegerField(db_index=True)
    department = models.CharField(max_length=100, db_index=True)
    current_allocated_bytes = models.BigIntegerField()
    requested_bytes = models.BigIntegerField(help_text="Bytes to add to user's quota")
    reason = models.TextField()
    status = models.CharField(
        max_length=30,
        choices=StorageExtensionStatus.choices,
        default=StorageExtensionStatus.SUBMITTED,
        db_index=True,
    )
    hod_user_id = models.IntegerField(null=True, blank=True)
    hod_comments = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "badms_storage_extension_request"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Storage Extension #{self.pk} for User {self.user_id} (+{self.requested_bytes} bytes: {self.status})"


class SpecialArchivalRecord(TimeStampedModel):
    """Immutable record for offline special archival of sensitive research data."""
    requester_name = models.CharField(max_length=150)
    requester_designation = models.CharField(max_length=150)
    dataset_title = models.CharField(max_length=255)
    classification = models.CharField(max_length=50, default="Sensitive Research Data")
    offline_media_type = models.CharField(
        max_length=100,
        help_text="e.g. LTO-8 Magnetic Tape, Encrypted Optical M-DISC, Air-gapped HSM",
    )
    media_serial_number = models.CharField(max_length=100)
    storage_vault_location = models.CharField(max_length=255)
    performed_by_user_id = models.IntegerField(db_index=True)
    notes = models.TextField(blank=True)
    completed_at = models.DateTimeField(default=timezone.now)
    checksum = models.CharField(max_length=64, blank=True)

    class Meta:
        db_table = "badms_special_archival_record"
        ordering = ["-completed_at"]

    def __str__(self) -> str:
        return f"Special Archival #{self.pk} for '{self.dataset_title}' ({self.offline_media_type}: {self.media_serial_number})"
