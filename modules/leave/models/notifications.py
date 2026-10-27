"""Durable delivery queue for leave workflow notifications."""
from django.db import models
from core.db.mixins import TimeStampedModel


class LeaveNotificationOutbox(TimeStampedModel):
    STATUS = [("pending", "Pending"), ("sending", "Sending"), ("sent", "Sent"), ("failed", "Failed")]
    recipient_user_id = models.IntegerField(db_index=True)
    topic = models.CharField(max_length=50)
    dedupe_key = models.CharField(max_length=180, unique=True)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=12, choices=STATUS, default="pending", db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    claimed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "leave_notification_outbox"
        ordering = ["created_at"]
