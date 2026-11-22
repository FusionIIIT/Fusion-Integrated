"""Scheduled tasks for Celery integration."""

from __future__ import annotations

import logging

from celery import shared_task

from modules.hreis.schedule import send_deadline_notifications, send_pending_action_reminders

logger = logging.getLogger("fusion.hreis.tasks")


@shared_task(
    name="hreis.send_pending_action_reminders",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def task_send_pending_action_reminders() -> int:
    """Send reminders for pending HR-EIS requests."""
    count = send_pending_action_reminders()
    logger.info("hreis.reminders.sent count=%d", count)
    return count


@shared_task(
    name="hreis.send_deadline_notifications",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def task_send_deadline_notifications() -> int:
    """Send appraisal deadline notifications to eligible faculty."""
    count = send_deadline_notifications()
    logger.info("hreis.deadlines.sent count=%d", count)
    return count
