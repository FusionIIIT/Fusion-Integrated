"""Scheduled work: ids in, nothing out but a report; each one idempotent under acks_late."""
from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.leave.tasks")


@shared_task(name="leave.deliver_notifications", acks_late=True, reject_on_worker_lost=True,
             soft_time_limit=270, time_limit=300)
def deliver_notifications(limit: int | None = None) -> str:
    from modules.leave.services import notifications

    report = notifications.deliver_pending(limit=limit)
    log.info("leave.notify.run %s", report)
    return str(report)


@shared_task(name="leave.process_sla", acks_late=True, reject_on_worker_lost=True,
             soft_time_limit=600, time_limit=700)
def process_sla() -> str:
    from modules.leave.services import sla

    return str(sla.process())


@shared_task(name="leave.year_boundary", acks_late=True, reject_on_worker_lost=True,
             soft_time_limit=3000, time_limit=3300)
def year_boundary() -> str:
    """Closes last year once, and credits this year; both are safe to repeat."""
    from django.utils import timezone

    from modules.leave.services import yearend

    year = timezone.localdate().year
    run = yearend.run(year - 1)
    credited = yearend.credit_year(year)
    return f"closed={year - 1}:{run.status} exceptions={len(run.exceptions)} credited={credited}"
