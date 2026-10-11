"""Scheduled work. Ids only in arguments; every task is idempotent."""
from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.elm.tasks")


@shared_task(name="elm.sla_sweep", acks_late=True, reject_on_worker_lost=True,
             soft_time_limit=270, time_limit=300)
def sla_sweep() -> str:
    """EL-UC-021."""
    from modules.elm.services import scheduled

    report = scheduled.sla_sweep()
    log.info("elm.sla.run %s", report)
    return str(report)


@shared_task(name="elm.year_end", acks_late=True, reject_on_worker_lost=True,
             soft_time_limit=1700, time_limit=1800)
def year_end(year: int | None = None) -> str:
    """EL-UC-020, for the year that just ended."""
    from modules.elm.services import scheduled

    report = scheduled.year_end(year or scheduled.previous_year())
    log.info("elm.year_end.run %s", report)
    return str(report)
