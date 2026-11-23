"""Celery tasks for Gymkhana."""

from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.gymkhana.tasks")


@shared_task(
    name="gymkhana.expire_polls",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def expire_polls() -> int:
    """Close voting polls past their expiration date."""
    from modules.gymkhana.services.polls import expire_overdue_polls

    count = expire_overdue_polls()
    if count:
        log.info("gymkhana.polls.expired count=%d", count)
    return count


@shared_task(
    name="gymkhana.deliver_notifications",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def deliver_notifications() -> int:
    """Send queued session, event and poll notifications."""
    from modules.gymkhana.services.notifications import deliver_pending

    sent = deliver_pending()
    if sent:
        log.info("gymkhana.notifications.sent count=%d", sent)
    return sent
