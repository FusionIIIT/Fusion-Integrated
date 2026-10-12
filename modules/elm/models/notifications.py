"""The notification outbox (BR-EL-035).

Written in the same transaction as the event that caused it, so a leave decision
and its email commit together. `dedupe_key` makes redelivery idempotent.
"""
from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel


class NotificationOutbox(TimeStampedModel):
    STATUS = [("pending", "Pending"), ("sending", "Sending"), ("sent", "Sent"),
              ("failed", "Failed"), ("suppressed", "Suppressed")]

    topic = models.CharField(max_length=64)
    dedupe_key = models.CharField(max_length=200, unique=True)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    recipient_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    recipient_email = models.CharField(max_length=254, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_notification_outbox"
        indexes = [
            models.Index(fields=["status", "created_at"],
                         name="elm_outbox_status_idx"),
        ]
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"outbox#{self.pk} {self.topic} {self.status}"
