"""The notification outbox (ADR-0006, BR-EL-035).

Every notification is written in the same transaction as the event that caused
it, so a task assignment and its email commit together and a mail outage can
never fail a leave decision. `dedupe_key` makes redelivery idempotent, and the
`pending → sending → sent` claim happens before the send so two workers cannot
deliver the same message twice.
"""
from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel

#: Topics ELM emits. Anything else is a programming error (BR-EL-035).
TOPICS: tuple[str, ...] = (
    "leave.request.submitted",
    "leave.substitute.nominated",
    "leave.substitute.accepted",
    "leave.substitute.declined",
    "leave.replacement_substitute.required",
    "leave.unit_head.reviewed",
    "leave.establishment.routed",
    "leave.decision.approved",
    "leave.decision.rejected",
    "leave.request.withdrawn",
    "leave.cancellation.requested",
    "leave.cancellation.decided",
    "leave.extension.requested",
    "leave.extension.decided",
    "leave.resumption.submitted",
    "leave.resumption.reviewed",
    "leave.offline_recorded",
    "leave.sla.reminder",
    "leave.sla.escalation",
    "leave.year_end.processed",
    "leave.year_end.exception",
)

PENDING = "pending"
SENDING = "sending"
SENT = "sent"
FAILED = "failed"
SUPPRESSED = "suppressed"

STATUSES: tuple[str, ...] = (PENDING, SENDING, SENT, FAILED, SUPPRESSED)

BROADCAST_SENTINEL = "leave-broadcast@invalid"


class NotificationOutbox(TimeStampedModel):
    topic = models.CharField(max_length=64, db_index=True)
    dedupe_key = models.CharField(max_length=200, unique=True)
    status = models.CharField(max_length=12, choices=[(s, s) for s in STATUSES],
                              default=PENDING, db_index=True)
    subject = models.CharField(max_length=200)
    body = models.TextField(blank=True, default="")
    recipient_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    recipient_email = models.EmailField(blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True, default="")
    claimed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("id",)
        indexes = [models.Index(fields=("status", "created_at"))]

    def __str__(self) -> str:
        return f"{self.topic} -> {self.recipient_user_id or self.recipient_email}"