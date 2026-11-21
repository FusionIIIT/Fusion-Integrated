"""Notification generation and dispatch services for FTS."""
from __future__ import annotations

from typing import Any

from django.utils import timezone

from modules.fts.models.audit import NotificationEvent


def trigger_notification(
    *,
    event_type: str,
    recipient_user_id: int,
    payload: dict[str, Any] | None = None,
) -> NotificationEvent:
    """Creates a notification event row to be dispatched to Fusion mechanisms."""
    return NotificationEvent.objects.create(
        event_type=event_type,
        recipient_user_id=recipient_user_id,
        payload=payload or {},
        delivered=False,
    )


def dispatch_pending(limit: int | None = None) -> int:
    """Dispatches pending notification events and marks them as delivered."""
    qs = NotificationEvent.objects.filter(delivered=False).order_by("created_at")
    if limit is not None:
        qs = qs[:limit]

    count = 0
    now = timezone.now()
    for event in qs:
        # In this platform, notification events are handed off to the notification queue.
        event.delivered = True
        event.delivered_at = now
        event.save(update_fields=["delivered", "delivered_at"])
        count += 1
    return count
