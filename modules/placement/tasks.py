"""Scheduled work.

Ids only in arguments, never ORM objects. Everything is idempotent, because
`acks_late` means a task can run twice if a worker dies mid-flight.
"""
from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.placement.tasks")


@shared_task(
    name="placement.deliver_notifications",
    acks_late=True, reject_on_worker_lost=True,
    soft_time_limit=270, time_limit=300,
)
def deliver_notifications(limit: int | None = None) -> str:
    """Drain the notification outbox (PC-BR-021).

    No autoretry — the rows carry their own attempts and backoff, so a failed
    pass is picked up by the next beat rather than re-sending the batch.
    """
    from modules.placement.services import notifications

    report = notifications.deliver_pending(limit=limit)
    log.info("placement.notify.run %s", report)
    return str(report)


@shared_task(
    name="placement.expire_overdue_offers",
    acks_late=True, reject_on_worker_lost=True,
    soft_time_limit=270, time_limit=300,
)
def expire_overdue_offers() -> int:
    """Close offers past their deadline (PC-BR-013), or a student who never
    answers stays blocked from the pool forever."""
    from modules.placement.services import offers

    n = offers.expire_overdue()
    if n:
        log.info("placement.offers.expired count=%d", n)
    return n


@shared_task(name="placement.rebuild_stats", acks_late=True)
def rebuild_stats(season: str) -> int:
    """Recompute the materialised statistics for a season."""
    from modules.placement.services import stats

    return stats.rebuild(season=season)
