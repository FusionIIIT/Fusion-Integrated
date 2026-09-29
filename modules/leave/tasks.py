"""Celery entry points. Ids and dates only, never ORM objects."""
from celery import shared_task

from modules.leave.services import scheduler, sla


@shared_task(name="leave.advance_lifecycle", acks_late=True,
             reject_on_worker_lost=True, soft_time_limit=120)
def advance_lifecycle() -> dict:
    report = scheduler.advance()
    return {"started": report.started, "ended": report.ended, "failed": report.failed}


@shared_task(name="leave.process_sla", acks_late=True,
             reject_on_worker_lost=True, soft_time_limit=120)
def process_sla() -> dict:
    report = sla.process()
    return {"reminded": report.reminded, "escalated": report.escalated,
            "still_open": report.still_open}
