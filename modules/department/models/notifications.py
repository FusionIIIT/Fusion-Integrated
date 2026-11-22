from django.db import models

from core.db.mixins import TimeStampedModel


class DepartmentNotification(TimeStampedModel):
    """Outbox row written in the event's own transaction and drained by a beat task (ADR-0006)."""

    PENDING, SENDING, SENT, FAILED = "pending", "sending", "sent", "failed"
    STATUS = [(PENDING, "Pending"), (SENDING, "Sending"), (SENT, "Sent"), (FAILED, "Failed")]

    topic = models.CharField(max_length=60)
    dedupe_key = models.CharField(max_length=200, unique=True)
    recipient_user_id = models.IntegerField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=8, choices=STATUS, default=PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "department_notification_outbox"
        indexes = [
            models.Index(fields=["status", "created_at"], name="dept_outbox_pending_idx"),
            models.Index(
                fields=["recipient_user_id", "-created_at"], name="dept_outbox_recipient_idx"
            ),
        ]
