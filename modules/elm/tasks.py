"""Scheduled work. Idempotent, because acks_late can run a task twice."""
from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.elm.tasks")


@shared_task(name="elm.year_end", acks_late=True, reject_on_worker_lost=True)
def year_end(year: int | None = None) -> int:
    from django.utils import timezone

    from modules.elm.services import year_end as svc

    run = svc.run(year or timezone.localdate().year - 1)
    return run.employees


@shared_task(name="elm.sla", acks_late=True, reject_on_worker_lost=True)
def sla() -> str:
    from modules.elm.services import sla as svc

    report = svc.process()
    log.info("elm.sla %s", report)
    return str(report)
