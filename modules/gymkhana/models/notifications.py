"""Notifications decided in the same transaction as their cause, drained by a task."""
from django.db import models

from core.db.mixins import TimeStampedModel


class NotificationOutbox(TimeStampedModel):
    STATUS = [("pending", "Pending"), ("sending", "Sending"), ("sent", "Sent"),
              ("failed", "Failed")]

    topic = models.CharField(max_length=60)
    dedupe_key = models.CharField(max_length=200, unique=True)
    recipient_user_id = models.IntegerField(null=True, blank=True)
    # A broadcast row carries no recipient; the drain expands it into per-student rows.
    is_broadcast = models.BooleanField(default=False)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "gymkhana_notification_outbox"
        indexes = [
            models.Index(fields=["status", "created_at"], name="gym_outbox_pending_idx"),
            models.Index(fields=["recipient_user_id", "created_at"],
                         name="gym_outbox_recipient_idx"),
        ]
