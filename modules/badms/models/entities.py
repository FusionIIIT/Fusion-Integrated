"""BADMS domain models."""
from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel


class BackupOperation(TimeStampedModel):
    """Tracks manual and scheduled backup operations (CFR-BA-001, 002, 004)."""
    TRIGGER_CHOICES = [("manual", "Manual"), ("scheduled", "Scheduled")]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    trigger_type = models.CharField(max_length=20, choices=TRIGGER_CHOICES, default="manual")
    dataset_code = models.CharField(max_length=100, default="all")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    initiated_by_user_id = models.IntegerField(null=True, blank=True)
    dump_location = models.CharField(max_length=255, blank=True)
    file_size_bytes = models.BigIntegerField(default=0)
    integrity_verified = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "badms_backup_operation"
        ordering = ["-created_at"]


class BackupSchedule(TimeStampedModel):
    """Global and local dataset backup schedules (CFR-BA-003, 014, BR-BA-011, 012)."""
    SCOPE_CHOICES = [("global", "Global"), ("local", "Local")]

    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, default="local")
    dataset_code = models.CharField(max_length=100, blank=True)  # Blank for global
    cron_expression = models.CharField(max_length=100)
    retention_days = models.IntegerField(default=30)
    is_active = models.BooleanField(default=True)
    configured_by_user_id = models.IntegerField()

    class Meta:
        db_table = "badms_backup_schedule"


class SecureArchivalRequest(TimeStampedModel, UserScopedModel):
    """Archival request lifecycle (CFR-BA-005..008, 010; Workflows BW-BA-01..03, CW-BA-01)."""
    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("hod_approved", "HoD Approved"),
        ("hod_rejected", "HoD Rejected"),
        ("classified", "Classified"),
        ("encryption_configured", "Encryption Configured"),
        ("completed", "Completed"),
        ("special_executed", "Special Executed"),
    ]
    TIER_CHOICES = [
        ("routine", "Routine"),
        ("sensitive", "Sensitive"),
        ("critical", "Critical"),
        ("archival", "Archival"),
    ]

    department = models.CharField(max_length=50)
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    file_size_bytes = models.BigIntegerField(default=0)
    reason = models.TextField()
    initial_classification = models.CharField(max_length=20, choices=TIER_CHOICES, default="routine")
    authoritative_classification = models.CharField(max_length=20, choices=TIER_CHOICES, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="submitted")

    # Review fields
    hod_reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    hod_remarks = models.TextField(blank=True)
    hod_reviewed_at = models.DateTimeField(null=True, blank=True)

    classified_by_user_id = models.IntegerField(null=True, blank=True)
    classified_at = models.DateTimeField(null=True, blank=True)

    is_encrypted = models.BooleanField(default=False)
    encryption_algorithm = models.CharField(max_length=50, blank=True)
    encryption_configured_by = models.IntegerField(null=True, blank=True)

    archive_location = models.CharField(max_length=255, blank=True)
    retention_until = models.DateTimeField(null=True, blank=True)
    is_special = models.BooleanField(default=False)

    class Meta:
        db_table = "badms_archival_request"
        ordering = ["-created_at"]


class DataRestorationRequest(TimeStampedModel, UserScopedModel):
    """Restoration request lifecycle (CFR-BA-011; Workflows BW-BA-06..07, CW-BA-03)."""
    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("sysadmin_approved", "SysAdmin Approved"),
        ("sysadmin_rejected", "SysAdmin Rejected"),
        ("completed", "Completed"),
    ]

    archival_request = models.ForeignKey(SecureArchivalRequest, on_delete=models.CASCADE, related_name="restorations")
    reason = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="submitted")
    sysadmin_reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    sysadmin_remarks = models.TextField(blank=True)
    restored_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "badms_restoration_request"
        ordering = ["-created_at"]


class StorageQuota(TimeStampedModel, UserScopedModel):
    """Monitors storage usage and thresholds per user (CFR-BA-013, BR-BA-016)."""
    allocated_mb = models.IntegerField(default=5120)  # 5 GB default
    used_mb = models.IntegerField(default=0)

    class Meta:
        db_table = "badms_storage_quota"


class StorageExtensionRequest(TimeStampedModel, UserScopedModel):
    """Storage extension requests reviewed by HoD (CFR-BA-012, 017; Workflows BW-BA-04..05, CW-BA-02)."""
    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    department = models.CharField(max_length=50)
    requested_additional_mb = models.IntegerField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="submitted")
    hod_reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    hod_remarks = models.TextField(blank=True)

    class Meta:
        db_table = "badms_storage_extension_request"
        ordering = ["-created_at"]


class BadmsAuditLog(TimeStampedModel):
    """Audit logging for user actions, admin actions, and security events (CFR-BA-018, 019)."""
    actor_user_id = models.IntegerField()
    actor_role = models.CharField(max_length=50)
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=50)
    entity_id = models.IntegerField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "badms_audit_log"
        ordering = ["-created_at"]
