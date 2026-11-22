"""Notification stubs for quiz events (BR-QZ-024).

Notifications are logged rather than dispatched until a delivery channel is
configured. This ensures failures do not affect quiz state (BR-QZ-024).
"""
from __future__ import annotations

import logging

logger = logging.getLogger("fusion.quiz.notifications")


def notify_quiz_published(*, quiz_id: int, title: str) -> None:
    logger.info("NOTIFY quiz_published quiz_id=%s title=%r", quiz_id, title)


def notify_attempt_submitted(*, attempt_id: int, user_id: int, quiz_id: int) -> None:
    logger.info(
        "NOTIFY attempt_submitted attempt_id=%s user_id=%s quiz_id=%s",
        attempt_id, user_id, quiz_id,
    )


def notify_result_released(*, attempt_id: int, user_id: int, quiz_id: int) -> None:
    logger.info(
        "NOTIFY result_released attempt_id=%s user_id=%s quiz_id=%s",
        attempt_id, user_id, quiz_id,
    )
