"""Archival and permanent purge models for System Admin."""
from django.db import models
from django.db.models import CheckConstraint, Q

from core.db.mixins import TimeStampedModel


class ArchivedUserRecord(TimeStampedModel):
    RETENTION_CHOICES = [
        ("standard_7yr", "Standard 7 Years"),
        ("permanent_audit", "Permanent Audit Record"),
    ]

    user_id = models.IntegerField(primary_key=True)
    institute_id = models.CharField(max_length=32, db_index=True)
    username = models.CharField(max_length=64, db_index=True)
    email = models.EmailField()
    user_type = models.CharField(max_length=16)
    reason = models.TextField()
    retention_option = models.CharField(
        max_length=32, choices=RETENTION_CHOICES, default="standard_7yr"
    )
    archived_by = models.IntegerField()
    archived_at = models.DateTimeField(db_index=True)
    reversible_until = models.DateTimeField(db_index=True)
    is_permanent = models.BooleanField(default=False, db_index=True)
    snapshot = models.JSONField(default=dict)

    class Meta:
        db_table = "system_admin_archived_user"
        ordering = ["-archived_at"]

    def __str__(self) -> str:
        return f"Archived User {self.username} (permanent={self.is_permanent})"


class HistoricalDatasetArchive(TimeStampedModel):
    category = models.CharField(max_length=64, db_index=True)
    description = models.TextField()
    date_range_start = models.DateField()
    date_range_end = models.DateField()
    record_count = models.PositiveIntegerField(default=0)
    backup_reference = models.CharField(max_length=255)
    archived_by = models.IntegerField()
    is_restored = models.BooleanField(default=False)
    restored_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "system_admin_dataset_archive"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Archive: {self.category} ({self.date_range_start} to {self.date_range_end})"


class PermanentPurgeRequest(TimeStampedModel):
    STATUS_CHOICES = [
        ("pending_it_head", "Pending IT Head Authorization"),
        ("approved", "Approved by IT Head"),
        ("rejected", "Rejected by IT Head"),
        ("purged", "Permanently Purged"),
    ]

    dataset_identifier = models.CharField(max_length=128, db_index=True)
    requested_by = models.IntegerField()
    requested_at = models.DateTimeField(auto_now_add=True)
    retention_verified = models.BooleanField(default=True)
    reason = models.TextField()
    status = models.CharField(
        max_length=32,
        choices=STATUS_CHOICES,
        default="pending_it_head",
        db_index=True,
    )
    it_head_user_id = models.IntegerField(null=True, blank=True)
    it_head_decided_at = models.DateTimeField(null=True, blank=True)
    it_head_remarks = models.TextField(blank=True)

    class Meta:
        db_table = "system_admin_purge_request"
        ordering = ["-created_at"]
        constraints = [
            CheckConstraint(
                condition=Q(status__in=["pending_it_head", "approved", "rejected", "purged"]),
                name="chk_sa_purge_status",
            ),
        ]

    def __str__(self) -> str:
        return f"PurgeRequest: {self.dataset_identifier} ({self.status})"
