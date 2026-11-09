"""Archived user records, historical dataset archives, and purge requests."""
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.system_admin.constants import PurgeRequestStatus, UserArchivalStatus


class ArchivedUserRecord(TimeStampedModel):
    """Preserves archived user data, snapshots, and reversibility windows (CW-SA-03, ISS-SA-004)."""

    basic_user_id = models.IntegerField(unique=True, primary_key=True)
    institute_id = models.CharField(max_length=32, db_index=True)
    username = models.CharField(max_length=64)
    email = models.EmailField()
    kind = models.CharField(max_length=16)
    archived_at = models.DateTimeField(auto_now_add=True, db_index=True)
    reversible_until = models.DateTimeField(db_index=True)  # BR-SA-005, ISS-SA-004
    status = models.CharField(
        max_length=32,
        choices=UserArchivalStatus.choices,
        default=UserArchivalStatus.REVERSIBLE,
        db_index=True,
    )
    archival_reason = models.TextField()
    authorized_by = models.IntegerField(help_text="Super Admin user_id")
    restored_at = models.DateTimeField(null=True, blank=True)
    restored_by = models.IntegerField(null=True, blank=True)
    restoration_reason = models.TextField(blank=True)
    finalized_permanent_at = models.DateTimeField(null=True, blank=True)
    user_data_snapshot = models.JSONField(help_text="Complete JSON serialized profile and role history")

    class Meta:
        db_table = "system_admin_archived_user"
        indexes = [
            models.Index(fields=["status", "reversible_until"]),
        ]

    def __str__(self):
        return f"ArchivedUser: {self.username} ({self.basic_user_id}) [{self.status}]"


class HistoricalDataArchive(TimeStampedModel):
    """Tracks bulk data moves to archive storage (BR-SA-017, BR-SA-018, BR-SA-019)."""

    dataset_category = models.CharField(max_length=64, db_index=True)
    date_range_start = models.DateField()
    date_range_end = models.DateField()
    record_count = models.PositiveIntegerField()
    backup_file_path = models.CharField(max_length=255)
    backup_checksum = models.CharField(max_length=64)
    archived_at = models.DateTimeField(auto_now_add=True)
    archived_by = models.IntegerField()
    retention_expires_at = models.DateField(db_index=True)
    is_restored = models.BooleanField(default=False)
    restored_at = models.DateTimeField(null=True, blank=True)
    is_purged = models.BooleanField(default=False)
    summary_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "system_admin_historical_data_archive"

    def __str__(self):
        return f"Archive: {self.dataset_category} ({self.date_range_start} to {self.date_range_end})"


class PurgeRequest(TimeStampedModel):
    """Encodes the dual-authorization workflow for permanent data purge (CW-SA-01, BR-SA-021, BR-SA-022)."""

    archive = models.ForeignKey(
        HistoricalDataArchive,
        on_delete=models.CASCADE,
        related_name="purge_requests",
    )
    status = models.CharField(
        max_length=24,
        choices=PurgeRequestStatus.choices,
        default=PurgeRequestStatus.PENDING_IT_HEAD,
        db_index=True,
    )
    requested_by = models.IntegerField(help_text="Super Admin who initiated the request")
    requested_at = models.DateTimeField(auto_now_add=True)
    request_reason = models.TextField()
    it_head_id = models.IntegerField(null=True, blank=True, help_text="IT Head who decided")
    it_head_decision_at = models.DateTimeField(null=True, blank=True)
    it_head_comments = models.TextField(blank=True)
    purged_at = models.DateTimeField(null=True, blank=True)
    purge_execution_summary = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "system_admin_purge_request"

    def __str__(self):
        return f"PurgeRequest #{self.id} for Archive {self.archive_id} [{self.status}]"
