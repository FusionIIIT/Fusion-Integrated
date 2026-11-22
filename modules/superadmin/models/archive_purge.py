"""Historical archive and dual-authorization purge models."""

from django.db import models

from core.db.mixins import TimeStampedModel


class ArchiveStatus(models.TextChoices):
    ARCHIVED = "ARCHIVED", "Archived"
    RESTORED = "RESTORED", "Restored"
    PURGED = "PURGED", "Purged"


class HistoricalArchiveRecord(TimeStampedModel):
    entity_type = models.CharField(max_length=64, db_index=True)
    record_identifier = models.CharField(max_length=128, db_index=True)
    payload = models.JSONField(default=dict)
    backup_reference = models.CharField(max_length=255)
    retention_period_days = models.IntegerField(default=1825)
    purge_eligible_at = models.DateTimeField(db_index=True)
    status = models.CharField(
        max_length=32,
        choices=ArchiveStatus.choices,
        default=ArchiveStatus.ARCHIVED,
        db_index=True,
    )
    archived_by_user_id = models.IntegerField()

    class Meta:
        db_table = "superadmin_historical_archive"


class PurgeRequestStatus(models.TextChoices):
    PENDING_AUTHORIZATION = "PENDING", "Pending Dual Authorization"
    AUTHORIZED = "AUTHORIZED", "Authorized"
    REJECTED = "REJECTED", "Rejected"
    COMPLETED = "COMPLETED", "Purge Executed"


class PurgeRequestRecord(TimeStampedModel):
    archive_record = models.ForeignKey(
        HistoricalArchiveRecord,
        on_delete=models.CASCADE,
        related_name="purge_requests",
    )
    requested_by_user_id = models.IntegerField()
    request_reason = models.TextField()
    status = models.CharField(
        max_length=32,
        choices=PurgeRequestStatus.choices,
        default=PurgeRequestStatus.PENDING_AUTHORIZATION,
        db_index=True,
    )
    authorized_by_user_id = models.IntegerField(null=True, blank=True)
    authorized_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")

    class Meta:
        db_table = "superadmin_purge_request"
