"""Scheduled work. Ids only in arguments; every task is safe to run twice."""

from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.oap.tasks")


@shared_task(
    name="oap.deliver_notifications",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def deliver_notifications(limit: int | None = None) -> dict:
    from modules.oap.services import notifications

    report = notifications.deliver_pending(limit=limit)
    log.info("oap.notify.run %s", report)
    return report


@shared_task(
    name="oap.send_pending_reminders",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def send_pending_reminders() -> dict:
    from modules.oap.services import reminders

    report = reminders.send_due_reminders()
    log.info("oap.reminders.run %s", report)
    return report
