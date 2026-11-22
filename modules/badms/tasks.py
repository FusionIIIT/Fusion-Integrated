"""Asynchronous backup task entry points."""
from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.badms.tasks")


@shared_task(
    name="badms.dispatch_scheduled_backups",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def dispatch_scheduled_backups() -> int:
    """Queue due schedules; work is idempotent within each schedule minute."""
    from modules.badms.services.scheduling import dispatch_due

    return dispatch_due()


@shared_task(
    name="badms.run_backup",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=4800,
    time_limit=5100,
)
def run_backup(run_id: int) -> str:
    """Execute a backup run through the configured BADMS adapter."""
    from modules.badms.services.backups import execute

    result = execute(run_id)
    log.info("badms.backup.completed run_id=%s status=%s", run_id, result)
    return result


@shared_task(
    name="badms.finalize_archival",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def finalize_archival(request_id: int) -> str:
    from modules.badms.services.workflows import finalize_archival_request

    result = finalize_archival_request(request_id)
    log.info("badms.archive.finalized request_id=%s status=%s", request_id, result)
    return result


@shared_task(
    name="badms.deliver_notifications",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def deliver_notifications(limit: int = 100) -> dict[str, int]:
    from modules.badms.services.notifications import deliver_pending

    report = deliver_pending(limit=limit)
    log.info("badms.notifications.delivered sent=%d failed=%d",
             report["sent"], report["failed"])
    return report


@shared_task(
    name="badms.monitor_storage",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def monitor_storage() -> int:
    from modules.badms.services.capacity import monitor_storage

    return monitor_storage()
