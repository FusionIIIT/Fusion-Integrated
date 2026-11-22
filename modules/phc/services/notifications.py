"""Notification service (PHC-BR-07, 11, 13; AFR-PHC-023, 026, 030)."""
from modules.phc.models.notifications import PHCNotification


def notify_user(
    recipient_user_id: int,
    notification_type: str,
    title: str,
    message: str,
) -> PHCNotification:
    """Creates an in-app notification for the recipient."""
    return PHCNotification.objects.create(
        recipient_user_id=recipient_user_id,
        notification_type=notification_type,
        title=title,
        message=message,
    )
