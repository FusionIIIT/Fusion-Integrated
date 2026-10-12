"""Celery tasks. Thin: they exist so the beat schedule has something to
call, and every rule lives in the services they delegate to."""
from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.leave")


@shared_task(name="leave.sweep_sla")
def sweep_sla() -> dict:
    from modules.leave.services import sla
    result = sla.sweep()
    if result["reminded"] or result["escalated"]:
        log.info("leave SLA sweep: %s", result)
    return result


@shared_task(name="leave.run_year_end")
def run_year_end() -> dict:
    """Processes the leave year that just closed; a no-op once marked, so a
    daily timer is safe even though the boundary bites once a year."""
    from modules.leave.services import policy as policy_service
    from modules.leave.services import yearend

    closing = policy_service.current_leave_year() - 1
    result = yearend.run_year_end(closing)
    if not result.get("already_run"):
        log.info("leave year-end %s: %s", closing, result)
    return result
