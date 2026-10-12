"""Scheduled work.

Ids only in arguments, never ORM objects. Everything is idempotent, because
`acks_late` means a task can run twice if a worker dies mid-flight.
"""
from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.elm.tasks")


@shared_task(
    name="elm.deliver_notifications",
    acks_late=True, reject_on_worker_lost=True,
    soft_time_limit=270, time_limit=300,
)
def deliver_notifications(limit: int | None = None) -> str:
    """Drain the notification outbox (BR-EL-035)."""
    from modules.elm.services import notifications

    report = notifications.deliver_pending(limit=limit)
    log.info("elm.notify.run %s", report)
    return str(report)


@shared_task(
    name="elm.process_sla",
    acks_late=True, reject_on_worker_lost=True,
    soft_time_limit=270, time_limit=300,
)
def process_sla() -> str:
    """Issue SLA reminders and escalations for stale tasks (BR-EL-032/033)."""
    from modules.elm.services import sla

    report = sla.process()
    log.info("elm.sla.run %s", report)
    return str(report)


@shared_task(
    name="elm.run_year_end",
    acks_late=True, reject_on_worker_lost=True,
    soft_time_limit=500, time_limit=600,
)
def run_year_end(year: int) -> str:
    """Apply year-end rules to one leave year (EL-UC-020).

    Deliberately not on a beat schedule: running it twice would double-lapse.
    Ops triggers it once per boundary, or the settings singleton decides.
    """
    from modules.elm.services import accounts

    report = accounts.year_end(year)
    log.info("elm.year_end.run year=%s %s", year, report)
    return str(report)
