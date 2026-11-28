"""Scheduled work; ids only in arguments, safe to run twice."""
from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.gymkhana.tasks")


@shared_task(name="gymkhana.deliver_notifications", acks_late=True,
             reject_on_worker_lost=True, soft_time_limit=270, time_limit=300)
def deliver_notifications(limit: int | None = None) -> str:
    """Drain the notification outbox; rows carry their own attempts, so no autoretry."""
    from modules.gymkhana.services import notifications

    report = notifications.deliver_pending(limit=limit)
    log.info("gymkhana.notify.run %s", report)
    return str(report)
