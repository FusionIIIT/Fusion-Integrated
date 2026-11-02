"""Notification service for emitting status updates and event alerts (CFR-HM-033, BR-HM-034)."""

from __future__ import annotations

from modules.hostel.domain.constants import NotificationEventType
from modules.hostel.models import HostelNotification


def emit_notification(
    recipient_user_id: int,
    title: str,
    message: str,
    event_type: NotificationEventType | str,
    link: str = "",
) -> HostelNotification:
    """Create a persistent notification record for the user."""
    return HostelNotification.objects.create(
        recipient_user_id=recipient_user_id,
        title=title,
        message=message,
        event_type=str(event_type),
        link=link,
    )
