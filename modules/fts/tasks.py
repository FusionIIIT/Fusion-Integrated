"""Celery asynchronous tasks for FTS."""
from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.fts.tasks")


@shared_task(
    name="fts.dispatch_pending_notifications",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def dispatch_pending_notifications(limit: int | None = None) -> int:
    """Dispatches pending notification events to Fusion notification mechanisms."""
    from modules.fts.services.notifications import dispatch_pending

    count = dispatch_pending(limit=limit)
    log.info("fts.notifications.dispatched count=%d", count)
    return count


@shared_task(
    name="fts.verify_audit_integrity",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def verify_audit_integrity() -> bool:
    """Validates chronological ordering and integrity of movement events."""
    from modules.fts.services.audit import verify_all_files_audit_integrity

    is_valid = verify_all_files_audit_integrity()
    log.info("fts.audit.integrity valid=%s", is_valid)
    return is_valid
