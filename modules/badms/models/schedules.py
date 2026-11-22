from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.db.mixins import TimeStampedModel


class BackupSchedule(TimeStampedModel):
    SCOPE_GLOBAL = "global"
    SCOPE_LOCAL = "local"
    SCOPE_CHOICES = [
        (SCOPE_GLOBAL, "Global"),
        (SCOPE_LOCAL, "Local"),
    ]

    name = models.CharField(max_length=150)
    scope_type = models.CharField(max_length=20, choices=SCOPE_CHOICES)
    dataset_name = models.CharField(max_length=100)
    cron_expression = models.CharField(max_length=100)
    data_classification_filter = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_by_user_id = models.IntegerField()
    version = models.IntegerField(default=1)
    effective_from = models.DateTimeField(default=timezone.now)
    effective_to = models.DateTimeField(null=True, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "badms_backup_schedule"
        constraints = [
            models.UniqueConstraint(
                fields=["dataset_name", "scope_type", "is_active"],
                condition=Q(is_active=True),
                name="uniq_badms_active_schedule_per_dataset",
            ),
            models.CheckConstraint(
                condition=Q(scope_type__in=["global", "local"]),
                name="chk_badms_sched_scope",
            ),
        ]
        indexes = [
            models.Index(fields=["is_active", "next_run_at"], name="idx_badms_sched_active_next"),
        ]
