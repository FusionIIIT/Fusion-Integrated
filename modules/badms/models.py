"""Database models for BADMS (Backup and Database Archive Management System).

Table naming convention: badms_<entity>
Adheres strictly to Fusion architecture:
- No cross-module ForeignKeys
- Independent app isolation
- Complete audit logging and transition tracking
"""

import uuid
from django.db import models
from django.utils import timezone


class BackupRecord(models.Model):
    """Stores manual and automatic database backup snapshots.
    
    Ref: CFR-BA-001, CFR-BA-002, BR-BA-001, BR-BA-014, BR-BA-015.
    """
    BACKUP_TYPE_CHOICES = [
        ("MANUAL", "Manual On-Demand"),
        ("AUTOMATIC", "Scheduled Automatic"),
        ("SPECIAL", "Special Archival Snapshot"),
    ]
    STATUS_CHOICES = [
        ("IN_PROGRESS", "In Progress"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    backup_type = models.CharField(max_length=20, choices=BACKUP_TYPE_CHOICES, default="MANUAL")
    dataset_name = models.CharField(max_length=100, default="primary_db", db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="IN_PROGRESS", db_index=True)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    file_path = models.CharField(max_length=500, blank=True)
    file_size_bytes = models.BigIntegerField(default=0)
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    triggered_by_user_id = models.CharField(max_length=64, db_index=True)
    error_message = models.TextField(blank=True)
    alert_sent = models.BooleanField(default=False)
    escalated_to_director = models.BooleanField(default=False)

    class Meta:
        db_table = "badms_backup_record"
        ordering = ["-started_at"]

    def __str__(self):
        return f"[{self.backup_type}] {self.dataset_name} ({self.status}) - {self.started_at.strftime('%Y-%m-%d %H:%M')}"


class BackupSchedule(models.Model):
    """Configures local (SysAdmin) and global (Super Admin) backup schedules.
    
    Ref: CFR-BA-003, CFR-BA-014, BR-BA-011, BR-BA-012, BR-BA-019.
    """
    SCOPE_CHOICES = [
        ("GLOBAL", "Global Institution Schedule"),
        ("LOCAL", "Dataset-Specific Local Schedule"),
    ]
    FREQUENCY_CHOICES = [
        ("HOURLY", "Hourly"),
        ("DAILY", "Daily"),
        ("WEEKLY", "Weekly"),
        ("MONTHLY", "Monthly"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, default="LOCAL", db_index=True)
    dataset_name = models.CharField(max_length=100, default="primary_db", db_index=True)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default="DAILY")
    scheduled_time = models.CharField(max_length=10, default="02:00")
    day_of_week = models.IntegerField(null=True, blank=True)  # 0=Monday .. 6=Sunday
    classification_filter = models.CharField(max_length=20, default="ALL")
    repository_path = models.CharField(max_length=500, default="/var/backups/fusion")
    is_active = models.BooleanField(default=True)
    created_by_user_id = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "badms_backup_schedule"
        ordering = ["scope", "dataset_name"]

    def __str__(self):
        return f"{self.name} [{self.scope}] - {self.dataset_name} ({self.frequency} at {self.scheduled_time})"


class StorageQuota(models.Model):
    """Tracks user and departmental storage usage against allocated limits.
    
    Ref: CFR-BA-012, CFR-BA-013, BR-BA-016, BA-UC-022.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.CharField(max_length=64, unique=True, db_index=True)
    department_id = models.CharField(max_length=64, db_index=True)
    allocated_storage_mb = models.DecimalField(max_digits=10, decimal_places=2, default=1024.0)  # 1 GB default
    used_storage_mb = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    threshold_percent = models.DecimalField(max_digits=5, decimal_places=2, default=80.0)
    is_alerted = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "badms_storage_quota"

    @property
    def usage_percentage(self) -> float:
        if self.allocated_storage_mb <= 0:
            return 0.0
        return float((self.used_storage_mb / self.allocated_storage_mb) * 100.0)

    def __str__(self):
        return f"User {self.user_id} ({self.department_id}): {self.used_storage_mb}/{self.allocated_storage_mb} MB ({self.usage_percentage:.1f}%)"


class ArchivalRequest(models.Model):
    """Tracks multi-stage secure archival submissions through HoD review and classification.
    
    Ref: CFR-BA-005, CFR-BA-006, CFR-BA-007, CW-BA-01, BW-BA-01, BW-BA-02, BW-BA-03.
    """
    STATUS_CHOICES = [
        ("SUBMITTED", "Submitted"),
        ("REJECTED", "Rejected by HoD"),
        ("HOD_APPROVED", "Approved by HoD"),
        ("CLASSIFIED_NON_SENSITIVE", "Classified Non-Sensitive / Policy Applied"),
        ("CLASSIFIED_SENSITIVE", "Classified Sensitive / Routed to IT Security"),
        ("SENSITIVE_ARCHIVE_ENCRYPTED", "Sensitive Archive Encrypted"),
        ("SPECIAL_ARCHIVED", "Special Archival Completed"),
    ]
    CLASSIFICATION_CHOICES = [
        ("ROUTINE", "Routine"),
        ("SENSITIVE", "Sensitive"),
        ("CRITICAL", "Critical"),
        ("ARCHIVAL", "Archival"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request_number = models.CharField(max_length=32, unique=True, db_index=True)
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50, default="DATA")
    file_size_mb = models.DecimalField(max_digits=10, decimal_places=2, default=10.0)
    attachment_ref = models.CharField(max_length=500, blank=True)
    requester_user_id = models.CharField(max_length=64, db_index=True)
    department_id = models.CharField(max_length=64, db_index=True)
    owners = models.CharField(max_length=255, blank=True)
    reason = models.TextField()
    
    initial_classification = models.CharField(
        max_length=20,
        choices=CLASSIFICATION_CHOICES,
        default="ROUTINE"
    )
    authoritative_classification = models.CharField(
        max_length=20,
        choices=CLASSIFICATION_CHOICES,
        blank=True
    )
    status = models.CharField(max_length=35, choices=STATUS_CHOICES, default="SUBMITTED", db_index=True)
    
    # Decision audit pointers
    hod_user_id = models.CharField(max_length=64, blank=True)
    hod_decision_date = models.DateTimeField(null=True, blank=True)
    hod_remarks = models.TextField(blank=True)
    
    classified_by_user_id = models.CharField(max_length=64, blank=True)
    classified_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "badms_archival_request"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.request_number}: {self.file_name} ({self.status}) [{self.department_id}]"


class EncryptedArchive(models.Model):
    """Stores the verified AES-256 encrypted archival record for Sensitive data.
    
    Ref: CFR-BA-008, BR-BA-003, BR-BA-007, BR-BA-008, BW-BA-03.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    archival_request = models.OneToOneField(
        ArchivalRequest,
        on_delete=models.CASCADE,
        related_name="encrypted_archive"
    )
    archive_code = models.CharField(max_length=64, unique=True, db_index=True)
    encryption_algorithm = models.CharField(max_length=32, default="AES-256")
    encrypted_at_rest = models.BooleanField(default=True)
    encrypted_in_transit = models.BooleanField(default=True)
    configured_by_user_id = models.CharField(max_length=64)
    archive_file_path = models.CharField(max_length=500)
    checksum_sha256 = models.CharField(max_length=64)
    retention_years = models.IntegerField(default=10)
    retention_expiry_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "badms_encrypted_archive"

    def __str__(self):
        return f"Archive {self.archive_code} ({self.encryption_algorithm}) - Valid until {self.retention_expiry_date}"


class StorageExtensionRequest(models.Model):
    """Workflow model for requesting additional departmental storage quota.
    
    Ref: CFR-BA-012, CW-BA-02, BW-BA-04, BW-BA-05, BR-BA-009, BR-BA-016, BR-BA-017.
    """
    STATUS_CHOICES = [
        ("SUBMITTED", "Submitted"),
        ("APPROVED", "Approved by HoD"),
        ("REJECTED", "Rejected by HoD"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request_number = models.CharField(max_length=32, unique=True, db_index=True)
    requester_user_id = models.CharField(max_length=64, db_index=True)
    department_id = models.CharField(max_length=64, db_index=True)
    requested_additional_mb = models.DecimalField(max_digits=10, decimal_places=2)
    current_usage_mb = models.DecimalField(max_digits=10, decimal_places=2)
    justification = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="SUBMITTED", db_index=True)
    
    hod_user_id = models.CharField(max_length=64, blank=True)
    hod_decision_date = models.DateTimeField(null=True, blank=True)
    hod_remarks = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "badms_storage_extension_request"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.request_number}: +{self.requested_additional_mb}MB for {self.requester_user_id} ({self.status})"


class RestorationRequest(models.Model):
    """Workflow model for archived data restoration requests.
    
    Ref: CFR-BA-011, CW-BA-03, BW-BA-06, BW-BA-07, BR-BA-005.
    """
    STATUS_CHOICES = [
        ("STANDARD_PENDING", "Restoration Requested / Standard Path"),
        ("SENSITIVE_PENDING_APPROVAL", "Sensitive Restoration Pending Approval"),
        ("REJECTED", "Rejected by SysAdmin"),
        ("APPROVED_FOR_RESTORATION", "Approved for Restoration"),
        ("RESTORED", "Restored"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request_number = models.CharField(max_length=32, unique=True, db_index=True)
    archival_request = models.ForeignKey(
        ArchivalRequest,
        on_delete=models.CASCADE,
        related_name="restoration_requests"
    )
    requester_user_id = models.CharField(max_length=64, db_index=True)
    department_id = models.CharField(max_length=64, db_index=True)
    reason = models.TextField()
    target_location = models.CharField(max_length=255, default="/restores/workspace")
    classification_snapshot = models.CharField(max_length=20)
    status = models.CharField(max_length=35, choices=STATUS_CHOICES, db_index=True)
    
    approved_by_user_id = models.CharField(max_length=64, blank=True)
    approval_date = models.DateTimeField(null=True, blank=True)
    approval_remarks = models.TextField(blank=True)
    
    restored_by_user_id = models.CharField(max_length=64, blank=True)
    restored_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "badms_restoration_request"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.request_number}: Restore {self.archival_request.file_name} ({self.status})"


class AuditEvent(models.Model):
    """Immutable audit trail for operational monitoring and security governance.
    
    Ref: CFR-BA-018, AFR-BA-061, AFR-BA-062, BA-UC-012, BA-UC-023, BR-BA-020.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    actor_user_id = models.CharField(max_length=64, db_index=True)
    actor_role = models.CharField(max_length=64)
    department_id = models.CharField(max_length=64, blank=True, db_index=True)
    event_type = models.CharField(max_length=64, db_index=True)
    target_entity_type = models.CharField(max_length=64)
    target_entity_id = models.CharField(max_length=64)
    details = models.JSONField(default=dict)
    ip_address = models.CharField(max_length=45, blank=True)

    class Meta:
        db_table = "badms_audit_event"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {self.actor_user_id} ({self.actor_role}) -> {self.event_type} on {self.target_entity_type}:{self.target_entity_id}"
