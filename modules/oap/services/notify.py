import logging

from modules.oap.domain import constants as c
from modules.oap.models.notification import OAPNotification

logger = logging.getLogger(__name__)


def emit_notification(
    recipient_user_id: int,
    title: str,
    message: str,
    related_entity_type: str = "",
    related_entity_id: int | None = None,
) -> list[OAPNotification]:
    """Emits system alerts and email notifications (OA-UC-91, OA-BR-03)."""
    notifications = []
    for channel in c.NOTIFICATION_CHANNELS:
        notif = OAPNotification.objects.create(
            recipient_user_id=recipient_user_id,
            title=title,
            message=message,
            channel=channel,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
        )
        notifications.append(notif)
        if channel == c.CHANNEL_EMAIL:
            logger.info("Simulated email to user %s: [%s] %s", recipient_user_id, title, message)
        else:
            logger.info("System alert to user %s: [%s] %s", recipient_user_id, title, message)
    return notifications


def send_pending_action_reminder(
    recipient_user_id: int,
    title: str,
    message: str,
    related_entity_type: str = "",
    related_entity_id: int | None = None,
) -> list[OAPNotification]:
    """Sends pending action reminders to responsible actors (OA-UC-92)."""
    return emit_notification(
        recipient_user_id=recipient_user_id,
        title=f"Reminder: {title}",
        message=message,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
    )
