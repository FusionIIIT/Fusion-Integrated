"""The notification outbox (BR-EL-032, BR-EL-033, BR-EL-035).

Written in the same transaction as the event that caused it and drained by a
separate worker, so a decision and its notification commit together or not at
all. `dedupe_key` makes redelivery idempotent.
"""

from django.db import models

from core.db.mixins import TimeStampedModel


class NotificationOutbox(TimeStampedModel):
    STATUS = [("pending", "Pending"), ("sending", "Sending"), ("sent", "Sent"),
              ("failed", "Failed"), ("suppressed", "Suppressed")]

    topic = models.CharField(max_length=48, db_index=True)
    dedupe_key = models.CharField(max_length=160, unique=True)
    recipient_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    recipient_email = models.EmailField(blank=True)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_notification_outbox"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["status", "created_at"],
                         name="leave_outbox_status_idx"),
            models.Index(fields=["recipient_user_id", "status"],
                         name="leave_outbox_recipient_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.topic} -> u{self.recipient_user_id} [{self.status}]"
