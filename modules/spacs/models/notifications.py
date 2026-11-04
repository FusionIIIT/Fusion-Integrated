"""Transactional Notification Outbox for SPACS.

Enforces:
- CFR-SPACS-015 (Lifecycle Notifications)
- BR-SPACS-008 (Notification on Significant Status Change)
- AFR-SPACS-048 (E-mail and in-dashboard notifications)
- Deduplicated enqueueing (dedupe_key) with distinguishable delivery states
- Notification failures never alter underlying application or task state
"""
from __future__ import annotations

from django.db import models
from core.db.mixins import TimeStampedModel


class SpacsNotificationOutbox(TimeStampedModel):
    """Transactional outbox for SPACS notifications.

    Written in the same database transaction as the business event that caused it.
    Deduplicated enqueueing is guaranteed by `dedupe_key`.
    Delivery status is tracked separately from task and application states.
    """

    STATUS_CHOICES = [
        ("pending", "Pending Delivery"),
        ("sending", "Sending"),
        ("sent", "Delivered / Sent"),
        ("failed", "Delivery Failed (Retryable)"),
        ("suppressed", "Suppressed (Permanent Failure / Daily Cap)"),
    ]

    topic = models.CharField(max_length=60, db_index=True)
    dedupe_key = models.CharField(max_length=200, unique=True, db_index=True)

    recipient_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    recipient_email = models.EmailField(blank=True)

    subject = models.CharField(max_length=200)
    body = models.TextField()
    payload = models.JSONField(default=dict, blank=True)

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending", db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "spacs_notification_outbox"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"], name="spacs_outbox_status_idx"),
            models.Index(fields=["recipient_user_id", "status"], name="spacs_outbox_recipient_idx"),
        ]

    def __str__(self) -> str:
        return f"[{self.status}] {self.topic} -> {self.recipient_user_id or self.recipient_email}"
