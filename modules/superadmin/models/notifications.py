from __future__ import annotations

from django.db import models
from django.db.models import Index
from django.utils import timezone

from core.db.mixins import TimeStampedModel


class NotificationOutbox(TimeStampedModel):
    recipient_id = models.PositiveIntegerField(db_index=True)
    recipient_email = models.EmailField()
    channel = models.CharField(max_length=16, default="email")
    template_code = models.CharField(max_length=64)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    status = models.CharField(max_length=16, default="pending", db_index=True)
    scheduled_for = models.DateTimeField(default=timezone.now, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    error_message = models.TextField(blank=True)
    context_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "superadmin_notification_outbox"
        indexes = [
            Index(fields=["status", "scheduled_for"], name="notif_outbox_stat_sched_idx"),
        ]
