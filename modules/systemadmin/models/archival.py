"""Archival and Permanent Purge Models for System Admin Control Plane."""
from django.db import models
from core.db.mixins import TimeStampedModel
from modules.systemadmin.models.user_mgmt import BasicUserProfile


class ArchivedUser(TimeStampedModel):
    STATUS_CHOICES = [
        ("reversible", "Reversible"),
        ("permanent_non_restorable", "Permanent / Non-Restorable"),
        ("restored", "Restored"),
    ]

    user = models.OneToOneField(
        BasicUserProfile,
        on_delete=models.CASCADE,
        related_name="archival_record"
    )
    archival_date = models.DateField(db_index=True)
    archived_at = models.DateTimeField(auto_now_add=True)
    archived_by = models.CharField(max_length=64)
    reason = models.TextField()
    retention_option = models.CharField(max_length=50, default="standard_institutional")
    reversibility_deadline = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="reversible", db_index=True)
    
    restored_at = models.DateTimeField(null=True, blank=True)
    restored_by = models.CharField(max_length=64, blank=True)
    restoration_authorization_ref = models.CharField(max_length=100, blank=True)

    retained_profile_snapshot = models.JSONField(default=dict)
    retained_role_history = models.JSONField(default=list)
    retained_module_metadata = models.JSONField(default=dict)

    class Meta:
        db_table = "systemadmin_archived_user"
        ordering = ["-archived_at"]

    def __str__(self) -> str:
        return f"Archived User: {self.user.institute_id} ({self.status})"


class ArchivedHistoricalData(TimeStampedModel):
    STATUS_CHOICES = [
        ("archived", "Archived"),
        ("restored", "Restored"),
        ("purged", "Purged"),
    ]

    category = models.CharField(max_length=64, db_index=True)
    date_range_start = models.DateField()
    date_range_end = models.DateField()
    archived_at = models.DateTimeField(auto_now_add=True)
    archived_by = models.CharField(max_length=64)
    record_count = models.PositiveIntegerField(default=0)
    storage_size_kb = models.PositiveIntegerField(default=0)
    backup_reference = models.CharField(max_length=120)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="archived", db_index=True)
    retention_expiry_date = models.DateField(db_index=True)
    summary_metadata = models.JSONField(default=dict)

    restored_at = models.DateTimeField(null=True, blank=True)
    restored_by = models.CharField(max_length=64, blank=True)
    restoration_approval_ref = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "systemadmin_archived_historical_data"
        ordering = ["-archived_at"]

    def __str__(self) -> str:
        return f"Archived Data: {self.category} ({self.date_range_start} to {self.date_range_end})"


class PermanentPurgeRequest(TimeStampedModel):
    TARGET_TYPE_CHOICES = [
        ("historical_data", "Historical Data"),
        ("archived_user", "Archived User"),
    ]

    STATUS_CHOICES = [
        ("pending_it_head", "Pending IT Head Authorization"),
        ("approved", "Permanently Purged"),
        ("rejected", "Purge Request Rejected; Data Remains Archived"),
    ]

    target_type = models.CharField(max_length=32, choices=TARGET_TYPE_CHOICES, default="historical_data")
    historical_data = models.ForeignKey(
        ArchivedHistoricalData,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="purge_requests"
    )
    archived_user = models.ForeignKey(
        ArchivedUser,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="purge_requests"
    )

    requested_by = models.CharField(max_length=64)  # Super Admin username
    requested_at = models.DateTimeField(auto_now_add=True)
    request_reason = models.TextField()
    super_admin_authenticated = models.BooleanField(default=True)

    status = models.CharField(max_length=64, choices=STATUS_CHOICES, default="pending_it_head", db_index=True)

    it_head_decided_by = models.CharField(max_length=64, blank=True)
    it_head_decided_at = models.DateTimeField(null=True, blank=True)
    it_head_decision = models.CharField(max_length=16, blank=True)  # approve or reject
    it_head_comments = models.TextField(blank=True)
    purge_executed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "systemadmin_permanent_purge_request"
        ordering = ["-requested_at"]

    def __str__(self) -> str:
        return f"Purge Request #{self.id}: {self.target_type} ({self.status})"
