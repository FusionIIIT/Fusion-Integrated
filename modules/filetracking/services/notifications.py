"""Notification triggering for File Tracking System (BR-FTS-013)."""

import logging
from typing import Any

from modules.filetracking.services.audit import record_audit

logger = logging.getLogger("fusion.filetracking.notify")

NOTIFICATION_TOPICS = {
    "file.received",
    "file.forwarded",
    "file.returned",
    "file.archived",
    "file.draft_created",
    "role.context_selected",
}


def trigger_file_notification(
    topic: str,
    recipient_user_id: int,
    file_id: int,
    file_number: str,
    subject: str,
    message: str,
    actor_user_id: int = 0,
    actor_designation: str = "System",
) -> dict[str, Any]:
    """Trigger a file notification event handed to Fusion notification mechanisms (BR-FTS-013)."""
    if topic not in NOTIFICATION_TOPICS:
        logger.warning("Unrecognized notification topic: %s", topic)

    payload = {
        "topic": topic,
        "recipient_user_id": recipient_user_id,
        "file_id": file_id,
        "file_number": file_number,
        "subject": subject,
        "message": message,
    }

    logger.info("Notification triggered: %s for user %s", topic, recipient_user_id)
    record_audit(
        action=f"notification.{topic}",
        actor_user_id=actor_user_id,
        actor_designation=actor_designation,
        file_id=file_id,
        payload=payload,
    )
    return payload
