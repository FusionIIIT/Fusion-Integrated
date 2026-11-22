"""Scheduled work; idempotent, because acks_late can run a task twice."""
from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.iaa.tasks")


@shared_task(name="iaa.escalate_overdue_approvals", acks_late=True,
             reject_on_worker_lost=True, soft_time_limit=270, time_limit=300)
def escalate_overdue_approvals() -> str:
    from modules.iaa.services import decisions

    report = decisions.escalate_overdue()
    log.info("iaa.escalation.run %s", report)
    return str(report)
