"""Notification triggering and event dispatch for CMS (AFR-CMS-055..063, BR-CMS-015, 031, 034)."""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("fusion.complaints.notifications")

NOTIFICATION_EVENTS: list[dict[str, Any]] = []


def emit_notification_event(
    event_type: str,
    payload: dict[str, Any],
    *,
    recipient_user_id: int | None = None,
) -> dict[str, Any]:
    """Trigger a complaint-related notification event.

    Per AFR-CMS-063, CMS limits responsibility to notification triggering.
    """
    event = {
        "event_type": event_type,
        "recipient_user_id": recipient_user_id,
        "payload": payload,
    }
    NOTIFICATION_EVENTS.append(event)
    log.info("CMS Notification Event triggered: %s for recipient=%s", event_type, recipient_user_id)
    return event


def clear_events_for_testing() -> None:
    """Clear recorded notification events in unit tests."""
    NOTIFICATION_EVENTS.clear()

