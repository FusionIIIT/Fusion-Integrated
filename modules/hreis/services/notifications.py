"""Notification service (BR-HR-024, AFR-077 to AFR-082)."""
from __future__ import annotations

from modules.hreis.models import HrNotification


def send_hr_notification(
    *,
    user_id: int,
    title: str,
    message: str,
    category: str = "submission",
    link: str = "",
) -> HrNotification:
    """Create in-app notification for request events, reminders, and policy updates."""
    return HrNotification.objects.create(
        user_id=user_id,
        title=title,
        message=message,
        category=category,
        link=link,
    )


def mark_notification_read(notification_id: int, user_id: int) -> bool:
    updated = HrNotification.objects.filter(id=notification_id, user_id=user_id).update(
        is_read=True
    )
    return updated > 0
