"""Leave tasks, and the beat entries that call them.

Tasks are named by string in `schedule.py` and only `tasks.py` imports them, so
config assembles the schedule without importing anything out of this module.
"""
from __future__ import annotations

import logging
from datetime import date

from celery import shared_task
from django.utils import timezone

from modules.leave.services import (
    notifications as notification_service,
    sla,
    year_end,
)

log = logging.getLogger("fusion.leave.tasks")


@shared_task(name="leave.deliver_notifications")
def deliver_notifications(limit: int | None = None) -> str:
    report = notification_service.deliver_pending(limit=limit)
    log.info("leave.notify %s", report)
    return str(report)


@shared_task(name="leave.send_sla_reminders")
def send_sla_reminders() -> int:
    """BR-EL-032: remind the person holding a task that it is waiting."""
    return sla.remind()


@shared_task(name="leave.escalate_overdue_tasks")
def escalate_overdue_tasks() -> int:
    """BR-EL-033: escalate a task that has passed its escalation threshold."""
    return sla.escalate()


@shared_task(name="leave.process_year_end")
def process_year_end(year: int | None = None, dry_run: bool = False) -> str:
    """BR-EL-001..009. `year` defaults to the year being closed: a run in
    December closes that year, and one run after New Year closes the year before,
    so a missed December run is not silently skipped."""
    today: date = timezone.now().date()
    closing = year if year is not None else (
        today.year if today.month >= 12 else today.year - 1)
    report = year_end.run(year=closing, dry_run=dry_run)
    log.info("leave.year_end %s", report)
    return str(report)