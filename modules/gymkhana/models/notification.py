"""Notification outbox for Gymkhana."""

from __future__ import annotations

from django.db import models
from django.db.models import CheckConstraint, Q

from core.db.mixins import TimeStampedModel
from modules.gymkhana.domain.constants import NOTIFICATION_PENDING, NOTIFICATION_STATUSES


class GymkhanaNotification(TimeStampedModel):
    """A notification written in the same transaction as the booking or poll it announces."""

    topic = models.CharField(max_length=40)
    dedupe_key = models.CharField(max_length=120, unique=True)
    # Empty on an announcement, which the worker expands into one row per recipient.
    recipient_user_id = models.IntegerField(null=True, blank=True)
    audience = models.JSONField(default=dict, blank=True)
    subject = models.CharField(max_length=300)
    body = models.TextField()
    status = models.CharField(max_length=12, default=NOTIFICATION_PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "gymkhana_notification"
        indexes = [
            models.Index(fields=["status", "created_at"], name="gym_notification_pending_idx"),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(status__in=NOTIFICATION_STATUSES),
                name="check_gymkhana_notification_status",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.topic} -> {self.recipient_user_id or 'audience'} ({self.status})"
