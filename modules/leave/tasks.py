"""Scheduled work for ELM.

Ids and primitives only in arguments, never ORM objects, and every task is
idempotent: `acks_late` means a task can run twice if a worker dies mid-flight.
The year-end run enforces that itself with a unique row per leave year.
"""
from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

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
    name="leave.process_sla",
    acks_late=True, reject_on_worker_lost=True,
    soft_time_limit=270, time_limit=300,
)
def process_sla() -> str:
    """Remind or escalate every pending task that has earned it (EL-UC-021)."""
    from modules.leave.services import sla

    report = sla.process()
    log.info("leave.sla.run %s", report)
    return str(report)


@shared_task(name="leave.execute_year_end", acks_late=True,
             soft_time_limit=540, time_limit=600)
def execute_year_end(leave_year: int) -> str:
    """EVT-01 — apply the year-end outcomes for one leave year (EL-UC-020)."""
    from core.api.exceptions import ConflictError
    from modules.leave.services import year_end

    try:
        run = year_end.run(leave_year=leave_year)
    except ConflictError as exc:
        log.info("leave.year_end.skipped year=%s code=%s", leave_year, exc.code)
        return f"skipped: {exc.code}"
    log.info("leave.year_end.run year=%s status=%s processed=%d", leave_year,
             run.status, run.accounts_processed)
    return f"{run.status} ({run.accounts_processed} account(s))"


@shared_task(name="leave.check_year_end_boundary", acks_late=True)
def check_year_end_boundary() -> str:
    """Fire EL-UC-020 on the day the *current* policy says the boundary falls.

    A fixed crontab date cannot express a configurable year-end boundary, and
    hard-coding one would quietly stop firing the year the boundary moves.
    """
    from modules.leave.services import year_end

    today = timezone.localdate()
    month, day = year_end.boundary_for(today.year)
    if (today.month, today.day) != (month, day):
        return "not the configured boundary"
    execute_year_end.delay(today.year)
    return f"dispatched year-end for {today.year}"
