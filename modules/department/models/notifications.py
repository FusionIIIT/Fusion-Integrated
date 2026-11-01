"""Department domain tables.

Institute people are referenced by plain `user_id` integers, never foreign
keys — there is no user table in this database.
"""

from django.db import models

from core.db.mixins import TimeStampedModel


class DepartmentNotification(TimeStampedModel):
    """A shared notification outbox for department events."""

    STATUS = [("pending", "Pending"), ("sending", "Sending"), ("sent", "Sent"),
              ("failed", "Failed")]

    topic = models.CharField(max_length=60, db_index=True)
    dedupe_key = models.CharField(max_length=200, unique=True)

    recipient_user_id = models.IntegerField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    payload = models.JSONField(default=dict, blank=True)

    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "department_notification"
        indexes = [
            models.Index(fields=["status", "created_at"], name="dept_outbox_pending_idx"),
            models.Index(fields=["recipient_user_id", "-created_at"],
                         name="dept_outbox_recipient_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.topic} -> {self.recipient_user_id}"
