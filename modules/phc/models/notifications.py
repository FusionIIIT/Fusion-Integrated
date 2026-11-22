from django.db import models

from core.db.mixins import TimeStampedModel


class NotificationOutbox(TimeStampedModel):
    event_key = models.CharField(max_length=160, unique=True)
    recipient_user_id = models.PositiveBigIntegerField()
    event_type = models.CharField(max_length=60)
    payload = models.JSONField(default=dict)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "phc_notification_outbox"
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["delivered_at", "created_at"],
                                name="phc_outbox_pending_idx")]


class Notification(TimeStampedModel):
    recipient_user_id = models.PositiveBigIntegerField()
    event_type = models.CharField(max_length=60)
    message = models.CharField(max_length=240)
    target_type = models.CharField(max_length=60)
    target_id = models.PositiveBigIntegerField()
    read_at = models.DateTimeField(null=True, blank=True)
    outbox = models.OneToOneField(NotificationOutbox, on_delete=models.PROTECT,
                                  related_name="notification")

    class Meta:
        db_table = "phc_notification"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["recipient_user_id", "-created_at"],
                                name="phc_notification_owner_idx")]
