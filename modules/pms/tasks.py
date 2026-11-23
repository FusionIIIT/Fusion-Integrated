"""Scheduled work. Ids only in arguments; every task is safe to run twice (acks_late)."""
from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.pms.tasks")
OPTIONS = {"acks_late": True, "reject_on_worker_lost": True, "soft_time_limit": 270,
           "time_limit": 300}


@shared_task(name="pms.deliver_notifications", **OPTIONS)
def deliver_notifications() -> str:
    from modules.pms.services import notifications

    return str(notifications.deliver_pending())


@shared_task(name="pms.process_deadlines", **{**OPTIONS, "soft_time_limit": 2700,
                                              "time_limit": 2900})
def process_deadlines() -> str:
    """BR-PMS-038, 097..104: expiry, 30/15/5-day alerts and missed-deadline escalations."""
    from modules.pms.services import deadlines

    return str(deadlines.sweep())


@shared_task(name="pms.auto_route_submissions", **OPTIONS)
def auto_route_submissions() -> int:
    from modules.pms.services import routing

    return routing.auto_route()


@shared_task(name="pms.run_scheduled_reports", **OPTIONS)
def run_scheduled_reports() -> int:
    from modules.pms.services import reports

    return reports.run_scheduled()
