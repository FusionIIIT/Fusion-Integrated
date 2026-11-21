"""Scheduled work. Arguments are plain values and every task is idempotent."""
from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.elm.tasks")


@shared_task(name="elm.sla_sweep", acks_late=True, reject_on_worker_lost=True,
             soft_time_limit=270, time_limit=300)
def sla_sweep() -> str:
    """Remind and escalate leave tasks left waiting (BR-EL-032/033)."""
    from modules.elm.services import sla

    report = sla.run()
    log.info("elm.sla.run %s", report)
    return str(report)


@shared_task(name="elm.year_end", acks_late=True, reject_on_worker_lost=True,
             soft_time_limit=1500, time_limit=1800)
def year_end(year: int | None = None) -> str:
    """Close the year just ended: lapse, convert VL to EL, carry forward (WF-EL-07)."""
    from django.utils import timezone

    from modules.elm.services import year_end as service

    report = service.run(year or timezone.localdate().year - 1)
    log.info("elm.year_end %s", report)
    return str(report)
