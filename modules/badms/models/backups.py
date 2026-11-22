from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.db.mixins import TimeStampedModel


class BackupRecord(TimeStampedModel):
    TYPE_MANUAL = "manual"
    TYPE_SCHEDULED = "scheduled"
    TYPE_CHOICES = [
        (TYPE_MANUAL, "Manual"),
        (TYPE_SCHEDULED, "Scheduled"),
    ]

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILURE = "failure"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILURE, "Failure"),
    ]

    backup_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    dataset_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    file_path = models.CharField(max_length=500, blank=True)
    file_size_bytes = models.BigIntegerField(default=0)
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)
    triggered_by_user_id = models.IntegerField(null=True, blank=True)
    consecutive_failure_count = models.IntegerField(default=0)
    alert_sent = models.BooleanField(default=False)

    class Meta:
        db_table = "badms_backup_record"
        constraints = [
            models.CheckConstraint(
                condition=Q(backup_type__in=["manual", "scheduled"]),
                name="chk_badms_backup_type",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["pending", "running", "success", "failure"]),
                name="chk_badms_backup_status",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="idx_badms_bkup_status_created"),
            models.Index(fields=["dataset_name", "-created_at"], name="idx_badms_bkup_ds_created"),
        ]
