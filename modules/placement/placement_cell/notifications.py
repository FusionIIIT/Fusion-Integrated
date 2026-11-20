"""Notification stubs for PCMS.

Each function logs the notification to the console.  In a production system
these would send emails, SMS, or push notifications.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def notify_application_submitted(student_id: str, posting_id: str) -> None:
    logger.info("NOTIFICATION: Student %s submitted application for posting %s", student_id, posting_id)


def notify_interview_scheduled(application_id: str, scheduled_at, mode: str) -> None:
    logger.info("NOTIFICATION: Interview scheduled for application %s at %s (%s)", application_id, scheduled_at, mode)


def notify_offer_extended(application_id: str, deadline) -> None:
    logger.info("NOTIFICATION: Offer extended for application %s, deadline %s", application_id, deadline)


def notify_offer_accepted(offer_id: str) -> None:
    logger.info("NOTIFICATION: Offer %s accepted", offer_id)


def notify_offer_rejected(offer_id: str) -> None:
    logger.info("NOTIFICATION: Offer %s rejected", offer_id)


def notify_announcement(title: str, content: str) -> None:
    logger.info("NOTIFICATION: Announcement published — %s", title)
