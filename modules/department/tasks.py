"""Scheduled work: ids only, idempotent, because acks_late can deliver a task twice."""

from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.department.tasks")


@shared_task(
    name="department.deliver_notifications",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=50,
    time_limit=55,
)
def deliver_notifications(limit: int | None = None) -> str:
    from modules.department.services import notifications

    report = notifications.deliver_pending(limit=limit)
    log.info("department.notify.run %s", report)
    return str(report)


@shared_task(
    name="department.apply_role_transitions",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=50,
    time_limit=55,
)
def apply_role_transitions() -> int:
    from modules.department.services import roles

    applied = roles.apply_transitions()
    if applied:
        log.info("department.roles.applied count=%d", applied)
    return applied
