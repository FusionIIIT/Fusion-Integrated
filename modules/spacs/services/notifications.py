"""Notification service for SPACS lifecycle events (CFR-SPACS-015, BR-SPACS-008)."""
from __future__ import annotations

from modules.spacs.models import SpacsNotification


def notify(
    *,
    recipient_user_id: int,
    recipient_role: str = "",
    event_type: str,
    title: str,
    message: str,
    reference_id: str = "",
    send_email: bool = True,
) -> SpacsNotification:
    """Dispatches in-app notification and queues email."""
    return SpacsNotification.objects.create(
        recipient_user_id=recipient_user_id,
        recipient_role=recipient_role,
        event_type=event_type,
        title=title,
        message=message,
        reference_id=str(reference_id),
        is_read=False,
        email_sent=send_email,
    )
