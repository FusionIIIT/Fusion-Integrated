"""BADMS persistence models.

Strict modular monolith rules:
1. No cross-module ForeignKeys. Plain indexed integers (e.g. user_id, department_id).
2. Inherits from TimeStampedModel and UserScopedModel from core.db.mixins.
"""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel


class BackupSchedule(TimeStampedModel):
    """Local and global automated backup configurations (CFR-BA-003, CFR-BA-014)."""

    name = models.CharField(max_length=120)
    scope = models.CharField(max_length=20, default="local")  # "global" | "local"
    dataset = models.CharField(max_length=80)  # dataset name or "all"
    frequency = models.CharField(
        max_length=20, default="daily"
    )  # "hourly", "daily", "weekly", "monthly"
    execution_time = models.CharField(max_length=5, default="02:00")  # "HH:MM"
    classification_filter = models.CharField(
        max_length=30, default="ALL"
    )  # "ALL", "CRITICAL", etc.
    repository_path = models.CharField(max_length=255, default="/var/backups/fusion")
    is_active = models.BooleanField(default=True)
    created_by_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = "badms_backup_schedule"
        constraints = [
            models.CheckConstraint(
                condition=Q(scope__in=["global", "local"]),
                name="badms_schedule_scope_valid",
            ),
            models.CheckConstraint(
                condition=Q(frequency__in=["hourly", "daily", "weekly", "monthly"]),
                name="badms_schedule_frequency_valid",
            ),
            models.UniqueConstraint(
                fields=["scope", "dataset"],
                name="badms_schedule_unique_scope_dataset",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.name} ({self.scope}/{self.dataset} - {self.frequency} at {self.execution_time})"
        )


class BackupRecord(TimeStampedModel):
    """Historical database dump and snapshot records (CFR-BA-001, CFR-BA-002, CFR-BA-004)."""

    schedule = models.ForeignKey(
        BackupSchedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="executions",
    )
    backup_type = models.CharField(max_length=20, default="automatic")  # "manual" | "automatic"
    status = models.CharField(
        max_length=20, default="pending"
    )  # "pending", "in_progress", "success", "failure"
    trigger_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    dataset = models.CharField(max_length=80, default="all")
    repository_path = models.CharField(max_length=255)
    artifact_path = models.CharField(max_length=255, blank=True)
    checksum = models.CharField(max_length=64, blank=True)
    size_bytes = models.BigIntegerField(default=0)
    is_consistent = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "badms_backup_record"
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["backup_type", "-created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(backup_type__in=["manual", "automatic"]),
                name="badms_backup_type_valid",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["pending", "in_progress", "success", "failure"]),
                name="badms_backup_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"Backup {self.id} [{self.backup_type}] - {self.status}"


class SystemState(TimeStampedModel):
    """Singleton/Key-value store for failure counts and system triggers (BR-BA-015)."""

    key = models.CharField(max_length=64, unique=True)
    value_int = models.IntegerField(default=0)
    value_str = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "badms_system_state"

    def __str__(self) -> str:
        return f"{self.key}={self.value_int}/{self.value_str}"


class UserStorageQuota(TimeStampedModel, UserScopedModel):
    """Tracks per-user storage allocations and full-quota state (CFR-BA-013, BR-BA-016)."""

    department_id = models.IntegerField(db_index=True)
    used_bytes = models.BigIntegerField(default=0)
    quota_bytes = models.BigIntegerField(default=10737418240)  # 10 GB default
    is_full = models.BooleanField(default=False)
    available_infra_bytes = models.BigIntegerField(default=1099511627776)  # 1 TB pool

    class Meta:
        db_table = "badms_user_storage_quota"
        constraints = [
            models.CheckConstraint(
                condition=Q(used_bytes__gte=0),
                name="badms_storage_used_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(quota_bytes__gt=0),
                name="badms_storage_quota_positive",
            ),
            models.UniqueConstraint(
                fields=["user_id"],
                name="badms_user_quota_unique_user",
            ),
        ]

    def __str__(self) -> str:
        return f"Quota User {self.user_id}: {self.used_bytes}/{self.quota_bytes}"


class ArchivalRequest(TimeStampedModel, UserScopedModel):
    """Secure Archival multi-stage entity (CFR-BA-005..008, CW-BA-01)."""

    department_id = models.IntegerField(db_index=True)
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    file_size_bytes = models.BigIntegerField(default=0)
    owners = models.CharField(max_length=255)  # owner usernames or roll numbers
    reason = models.TextField()
    attachment_path = models.CharField(max_length=500)
    initial_classification = models.CharField(max_length=20, default="routine")
    authoritative_classification = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=35, default="submitted")

    # HoD Decision
    hod_id = models.IntegerField(null=True, blank=True, db_index=True)
    hod_decided_at = models.DateTimeField(null=True, blank=True)
    hod_rejection_reason = models.TextField(blank=True)

    # SysAdmin Classification
    classified_by_id = models.IntegerField(null=True, blank=True, db_index=True)
    classified_at = models.DateTimeField(null=True, blank=True)

    # IT Security Encryption
    security_officer_id = models.IntegerField(null=True, blank=True, db_index=True)
    encryption_algorithm = models.CharField(max_length=50, blank=True)  # AES-256
    encrypted_archive_path = models.CharField(max_length=500, blank=True)
    encryption_configured_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "badms_archival_request"
        indexes = [
            models.Index(fields=["department_id", "status"]),
            models.Index(fields=["user_id", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    status__in=[
                        "submitted",
                        "hod_approved",
                        "rejected",
                        "classified_non_sensitive",
                        "classified_sensitive",
                        "sensitive_archive_encrypted",
                    ]
                ),
                name="badms_archival_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(
                    initial_classification__in=["critical", "sensitive", "routine", "archival"]
                ),
                name="badms_archival_initial_class_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"ArchivalRequest {self.id} ({self.file_name}) - {self.status}"


class SpecialArchivalRecord(TimeStampedModel):
    """Super Admin direct offline-initiated archival record (CFR-BA-010, BR-BA-018)."""

    dataset_name = models.CharField(max_length=150)
    source_authority = models.CharField(max_length=150)  # Offline originator reference
    reason = models.TextField()
    classification = models.CharField(max_length=20, default="sensitive")
    archive_path = models.CharField(max_length=500)
    performed_by_id = models.IntegerField(db_index=True)  # Super Admin user_id
    size_bytes = models.BigIntegerField(default=0)
    checksum = models.CharField(max_length=64, blank=True)

    class Meta:
        db_table = "badms_special_archival_record"

    def __str__(self) -> str:
        return f"SpecialArchive {self.dataset_name} by {self.performed_by_id}"


class StorageExtensionRequest(TimeStampedModel, UserScopedModel):
    """User storage expansion request (CFR-BA-012, CW-BA-02)."""

    department_id = models.IntegerField(db_index=True)
    requested_bytes = models.BigIntegerField()
    current_usage_bytes = models.BigIntegerField()
    current_quota_bytes = models.BigIntegerField()
    justification = models.TextField()
    attachment_path = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=20, default="submitted")

    hod_id = models.IntegerField(null=True, blank=True, db_index=True)
    hod_decided_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        db_table = "badms_storage_extension_request"
        indexes = [
            models.Index(fields=["department_id", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(requested_bytes__gt=0),
                name="badms_extension_bytes_positive",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["submitted", "approved", "rejected"]),
                name="badms_extension_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"ExtensionRequest {self.id} User {self.user_id} - {self.status}"


class RestorationRequest(TimeStampedModel, UserScopedModel):
    """Archived data restoration requests (CFR-BA-011, CW-BA-03)."""

    archival_request = models.ForeignKey(
        ArchivalRequest,
        on_delete=models.CASCADE,
        related_name="restorations",
    )
    classification = models.CharField(max_length=20)  # Snapshot from archival_request
    reason = models.TextField()
    target_destination = models.CharField(max_length=255)
    status = models.CharField(max_length=30, default="requested_standard")

    sysadmin_id = models.IntegerField(null=True, blank=True, db_index=True)
    sysadmin_decided_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    restored_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "badms_restoration_request"
        indexes = [
            models.Index(fields=["user_id", "status"]),
            models.Index(fields=["status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    status__in=[
                        "requested_standard",
                        "pending_approval",
                        "approved",
                        "rejected",
                        "restored",
                    ]
                ),
                name="badms_restoration_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"Restoration {self.id} for Archive {self.archival_request_id} - {self.status}"


class AuditLog(TimeStampedModel):
    """Tamper-evident audit trail (CFR-BA-018, BA-UC-023)."""

    actor_id = models.IntegerField(null=True, blank=True, db_index=True)
    actor_username = models.CharField(max_length=100, blank=True)
    actor_role = models.CharField(max_length=50, blank=True)
    event_source = models.CharField(
        max_length=30, default="user"
    )  # "user", "admin", "system", "security"
    action = models.CharField(max_length=120)
    resource_type = models.CharField(max_length=80)
    resource_id = models.CharField(max_length=80, blank=True)
    department_id = models.IntegerField(null=True, blank=True, db_index=True)
    outcome = models.CharField(max_length=20, default="success")  # "success", "failure", "denied"
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.CharField(max_length=45, blank=True)

    class Meta:
        db_table = "badms_audit_log"
        indexes = [
            models.Index(fields=["event_source", "-created_at"]),
            models.Index(fields=["actor_id", "-created_at"]),
            models.Index(fields=["department_id", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"AuditLog {self.created_at} [{self.event_source}] {self.action}: {self.outcome}"


class SecurityPolicy(TimeStampedModel):
    """IT Security configurable controls (CFR-BA-019, BA-UC-020)."""

    key = models.CharField(max_length=60, unique=True)
    policy_name = models.CharField(max_length=120)
    encryption_algorithm = models.CharField(max_length=40, default="AES-256")
    is_enforced = models.BooleanField(default=True)
    parameters = models.JSONField(default=dict, blank=True)
    updated_by_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = "badms_security_policy"

    def __str__(self) -> str:
        return f"SecurityPolicy {self.policy_name} (Enforced: {self.is_enforced})"


class NotificationLog(TimeStampedModel):
    """Notification dispatch log (CFR-BA-016, CFR-BA-017, BR-BA-014, BR-BA-015)."""

    recipient_id = models.IntegerField(null=True, blank=True, db_index=True)
    recipient_email = models.CharField(max_length=150, blank=True)
    recipient_role = models.CharField(max_length=50)
    notification_type = models.CharField(max_length=60)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    is_delivered = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "badms_notification_log"

    def __str__(self) -> str:
        return f"Notification to {self.recipient_role}: Delivered={self.is_delivered}"
