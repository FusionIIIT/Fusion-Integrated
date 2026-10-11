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
    from modules.leave.services import notifications

    report = notifications.deliver_pending(limit=limit)
    log.info("leave.notify.run %s", report)
    return str(report)


@shared_task(
    name="leave.process_sla",
    acks_late=True, reject_on_worker_lost=True,
    soft_time_limit=270, time_limit=300,
)
def process_sla() -> dict:
    from modules.leave.services import sla

    report = sla.process_due()
    log.info("leave.sla.run %s", report)
    return report


@shared_task(
    name="leave.run_year_end",
    acks_late=True, reject_on_worker_lost=True,
    soft_time_limit=3600, time_limit=3900,
)
def run_year_end(year: int | None = None) -> dict:
    from modules.leave.services import yearend

    report = yearend.run_year_end(year=year)
    log.info("leave.yearend.run %s", report)
    return report
