from django.db import models

from core.db.mixins import TimeStampedModel


class GymkhanaNotificationOutbox(TimeStampedModel):
    recipient_user_id = models.IntegerField(db_index=True)
    topic = models.CharField(max_length=100)
    subject = models.CharField(max_length=250)
    body = models.TextField()
    status = models.CharField(
        max_length=20,
        default="pending",
    )

    class Meta:
        db_table = "gymkhana_notification_outbox"
