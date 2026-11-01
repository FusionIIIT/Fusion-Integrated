"""Scheduled work.

Ids only in arguments, never ORM objects. Everything here is idempotent, because
`acks_late` means a task can run twice if a worker dies mid-flight.
"""
from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.leave.tasks")


@shared_task(
    name="leave.deliver_notifications",
    acks_late=True, reject_on_worker_lost=True,
    soft_time_limit=270, time_limit=300,
)
def deliver_notifications(limit: int | None = None) -> str:
    """Drain the notification outbox (BR-EL-035)."""
    from modules.leave.services import notifications

    report = notifications.deliver_pending(limit=limit)
    log.info("leave.notify.run %s", report)
    return str(report)


@shared_task(
    name="leave.run_sla_sweep",
    acks_late=True, reject_on_worker_lost=True,
    soft_time_limit=270, time_limit=300,
)
def run_sla_sweep() -> str:
    """Remind and escalate the tasks still waiting (EL-UC-021)."""
    from modules.leave.services import sla

    report = sla.sweep()
    log.info("leave.sla.run %s", report)
    return str(report)


@shared_task(
    name="leave.run_year_end",
    acks_late=True, reject_on_worker_lost=True,
    soft_time_limit=1800, time_limit=1900,
)
def run_year_end(year: int | None = None) -> str:
    """Settle the years that are over (EL-UC-020).

    A static schedule cannot name a year, and hard-coding one would silently
    stop settling the day the calendar rolls over.
    """
    from modules.leave.services import yearend

    years = [year] if year is not None else yearend.years_to_settle()
    for target in years:
        report = yearend.run(year=target)
        log.info("leave.yearend %s exceptions=%d", target,
                 len(report["exceptions"]))
    return f"settled {years}"
