"""Reliable notification outbox queue models (AFR-SA-068..071B, BR-SA-023, BR-SA-032)."""
from django.db import models
from django.utils import timezone

from core.db.mixins import TimeStampedModel
from modules.system_admin.constants import NotificationChannel, NotificationStatus


class NotificationOutbox(TimeStampedModel):
    """Reliable notification outbox pattern."""

    id = models.BigAutoField(primary_key=True)
    recipient_id = models.IntegerField(db_index=True)
    recipient_email = models.EmailField(blank=True)
    recipient_phone = models.CharField(max_length=20, blank=True)
    channel = models.CharField(
        max_length=16,
        choices=NotificationChannel.choices,
        default=NotificationChannel.EMAIL,
    )
    template_code = models.CharField(max_length=48)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(
        max_length=16,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
        db_index=True,
    )
    retry_count = models.PositiveSmallIntegerField(default=0)
    scheduled_for = models.DateTimeField(default=timezone.now, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    context_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "system_admin_notification_outbox"
        indexes = [
            models.Index(fields=["status", "scheduled_for"]),
        ]

    def __str__(self):
        return f"Notification #{self.id} [{self.channel}] to User {self.recipient_id} ({self.status})"
