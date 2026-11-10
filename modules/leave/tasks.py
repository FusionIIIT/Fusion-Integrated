"""Scheduled work; both tasks are idempotent because postings and notices are keyed."""
from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

log = logging.getLogger("fusion.leave.tasks")


@shared_task(name="leave.process_sla", acks_late=True, reject_on_worker_lost=True)
def process_sla() -> str:
    from modules.leave.services import periodic

    report = periodic.process_sla(timezone.now())
    log.info("leave.sla %s", report)
    return str(report)


@shared_task(name="leave.year_end", acks_late=True, reject_on_worker_lost=True)
def year_end(year: int | None = None) -> str:
    from modules.leave.services import periodic

    report = periodic.run_year_end(year or timezone.localdate().year - 1)
    log.info("leave.year_end %s", report)
    return str(report)
