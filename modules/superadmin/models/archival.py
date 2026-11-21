from __future__ import annotations

from django.db import models
from django.db.models import F, Index, Q

from core.db.mixins import TimeStampedModel
from modules.superadmin.domain.constants import (
    ALL_ARCHIVAL_STATUSES,
    ALL_PURGE_STATUSES,
    ARCHIVAL_STATUS_REVERSIBLE,
    PURGE_STATUS_PENDING_IT_HEAD,
)


class ArchivedUserRecord(TimeStampedModel):
    user_id = models.PositiveIntegerField(primary_key=True)
    institute_id = models.CharField(max_length=32, db_index=True)
    username = models.CharField(max_length=150, db_index=True)
    email = models.EmailField()
    user_kind = models.CharField(max_length=16)
    status = models.CharField(
        max_length=24,
        choices=[(s, s) for s in sorted(ALL_ARCHIVAL_STATUSES)],
        default=ARCHIVAL_STATUS_REVERSIBLE,
        db_index=True,
    )
    archived_at = models.DateTimeField(db_index=True)
    reversible_until = models.DateTimeField(db_index=True)
    authorized_by = models.PositiveIntegerField()
    archival_reason = models.TextField()
    restored_at = models.DateTimeField(null=True, blank=True)
    restored_by = models.PositiveIntegerField(null=True, blank=True)
    restoration_reason = models.TextField(blank=True)
    finalized_permanent_at = models.DateTimeField(null=True, blank=True)
    metadata_snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "superadmin_archived_user"
        constraints = [
            models.CheckConstraint(
                condition=Q(reversible_until__gte=F("archived_at")),
                name="archived_user_reversible_deadline_valid",
            ),
        ]
        indexes = [
            Index(fields=["status", "reversible_until"], name="arch_usr_stat_dead_idx"),
            Index(fields=["institute_id", "status"], name="arch_usr_inst_stat_idx"),
        ]


class HistoricalDataArchive(TimeStampedModel):
    dataset_category = models.CharField(max_length=64, db_index=True)
    title = models.CharField(max_length=200)
    date_range_start = models.DateField()
    date_range_end = models.DateField()
    record_count = models.PositiveIntegerField()
    backup_file_path = models.CharField(max_length=255)
    backup_checksum = models.CharField(max_length=64)
    retention_expires_at = models.DateField(db_index=True)
    is_restored = models.BooleanField(default=False)
    restored_at = models.DateTimeField(null=True, blank=True)
    is_purged = models.BooleanField(default=False, db_index=True)
    archived_by = models.PositiveIntegerField()
    summary_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "superadmin_historical_archive"
        constraints = [
            models.CheckConstraint(
                condition=Q(date_range_end__gte=F("date_range_start")),
                name="hist_archive_date_range_valid",
            ),
            models.CheckConstraint(
                condition=Q(retention_expires_at__gte=F("date_range_end")),
                name="hist_archive_retention_valid",
            ),
        ]
        indexes = [
            Index(fields=["dataset_category", "is_purged"], name="hist_arch_cat_purge_idx"),
        ]


class PurgeRequest(TimeStampedModel):
    archive = models.ForeignKey(
        HistoricalDataArchive, on_delete=models.PROTECT, related_name="purge_requests"
    )
    status = models.CharField(
        max_length=24,
        choices=[(s, s) for s in sorted(ALL_PURGE_STATUSES)],
        default=PURGE_STATUS_PENDING_IT_HEAD,
        db_index=True,
    )
    requested_by = models.PositiveIntegerField()
    requested_at = models.DateTimeField(auto_now_add=True, db_index=True)
    request_reason = models.TextField()
    it_head_id = models.PositiveIntegerField(null=True, blank=True)
    it_head_decision_at = models.DateTimeField(null=True, blank=True)
    it_head_comments = models.TextField(blank=True)
    purged_at = models.DateTimeField(null=True, blank=True)
    execution_summary = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "superadmin_purge_request"
        constraints = [
            models.CheckConstraint(
                condition=~Q(requested_by=F("it_head_id")),
                name="purge_dual_auth_distinct_actors",
            ),
        ]
        indexes = [
            Index(fields=["status", "requested_at"], name="purge_req_status_req_idx"),
        ]
