"""Notification ledger service for BADMS."""
from __future__ import annotations

from modules.badms.models import BadmsNotification


def send_notification(
    *,
    user_id: int,
    subject: str,
    message: str,
    notification_type: str,
    recipient_role: str = "",
    related_object_id: str | int = "",
) -> BadmsNotification:
    """Create and record an in-system notification for a user or role."""
    return BadmsNotification.objects.create(
        user_id=user_id,
        recipient_role=recipient_role or "",
        subject=subject,
        message=message,
        notification_type=notification_type,
        related_object_id=str(related_object_id) if related_object_id else "",
    )
