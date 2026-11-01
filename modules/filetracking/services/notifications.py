"""Notification triggering for File Tracking System (FTS).

Implements BR-FTS-013 and AFR-FTS-061..066.
Triggers notifications for:
- File received
- File forwarded
- File returned
- File archived
- Role assigned / reassigned
"""
import logging
from typing import Any

log = logging.getLogger("fusion.fts.notify")

NOTIFICATION_TOPICS = {
    "file.received": "File received in inbox",
    "file.forwarded": "File forwarded to recipient",
    "file.returned": "File returned to sender",
    "file.archived": "File archived by owner",
    "role.assigned": "FTS role assigned or reassigned",
}


def trigger_fts_notification(
    event_type: str,
    recipient_user_id: int,
    file_id: int | None = None,
    subject: str = "",
    message: str = "",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Trigger an FTS notification event (BR-FTS-013).

    Delivery is handed off to Fusion integrated notification mechanism.
    """
    event_data = {
        "event_type": event_type,
        "recipient_user_id": recipient_user_id,
        "file_id": file_id,
        "subject": subject,
        "message": message,
        "payload": payload or {},
    }
    log.info(
        "FTS notification triggered: %s to user %s for file %s",
        event_type,
        recipient_user_id,
        file_id,
    )
    return event_data
