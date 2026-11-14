from django.db import models

from core.db.mixins import TimeStampedModel
from modules.oap.domain import constants as c


class OAPNotification(TimeStampedModel):
    """System-generated alert and notification log (OA-UC-91, OA-UC-92, OA-BR-03)."""

    recipient_user_id = models.IntegerField(db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    channel = models.CharField(
        max_length=30,
        choices=[(ch, ch) for ch in c.NOTIFICATION_CHANNELS],
        default=c.CHANNEL_SYSTEM_ALERT,
    )
    related_entity_type = models.CharField(max_length=50, blank=True)
    related_entity_id = models.IntegerField(null=True, blank=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
