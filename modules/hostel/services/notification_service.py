"""Notification service for HM events (3.13, CFR-HM-038, BR-HM-034)."""

from ..models import NotificationRecord


def create_notification(
    recipient_user_id: int,
    event_type: str,
    title: str,
    message: str,
    reference_id: str = "",
) -> NotificationRecord:
    """Issue in-app notification to a user."""
    return NotificationRecord.objects.create(
        recipient_user_id=recipient_user_id,
        event_type=event_type,
        title=title,
        message=message,
        reference_id=str(reference_id),
    )
