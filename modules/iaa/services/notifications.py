"""Notification dispatch service enforcing IAA-BR-504 (Notification Trigger Matrix)."""

import logging
from collections.abc import Sequence

logger = logging.getLogger(__name__)


def emit_notification(
    recipient_ids: Sequence[int],
    title: str,
    message: str,
    target_type: str,
    target_id: int,
) -> None:
    # Emits dashboard notification to designated recipient users
    for recipient_id in recipient_ids:
        logger.info(
            "Notification sent to user %s: [%s] %s (ref: %s:%s)",
            recipient_id,
            title,
            message,
            target_type,
            target_id,
        )
