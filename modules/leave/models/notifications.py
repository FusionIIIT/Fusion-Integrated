from django.db import models
from core.db.mixins import TimeStampedModel

class LeaveNotificationOutbox(TimeStampedModel):
    recipient_user_id = models.IntegerField(db_index=True)
    topic = models.CharField(max_length=100)
    dedupe_key = models.CharField(max_length=150, unique=True)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    status = models.CharField(
        max_length=20,
        default="pending",
        choices=[("pending", "Pending"), ("delivered", "Delivered"), ("failed", "Failed")]
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True)

    class Meta:
        db_table = "leave_notification_outbox"
        ordering = ["created_at"]