"""Scheduled background tasks for SPACS.

Enforces:
- acks_late=True, reject_on_worker_lost=True for idempotent execution.
- Operational worker tasks for draining notification outbox and SLA monitoring.
"""
from __future__ import annotations

import logging
from celery import shared_task

log = logging.getLogger("fusion.spacs.tasks")


@shared_task(
    name="spacs.deliver_notifications",
    acks_late=True, reject_on_worker_lost=True,
    soft_time_limit=270, time_limit=300,
)
def deliver_notifications(limit: int | None = None) -> str:
    """Drains pending notifications from the SPACS outbox."""
    from modules.spacs.services.notifications import deliver_pending

    report = deliver_pending(limit=limit or 200)
    log.info("spacs.notify.run %s", report)
    return str(report)


@shared_task(
    name="spacs.process_sla_reminders",
    acks_late=True, reject_on_worker_lost=True,
    soft_time_limit=270, time_limit=300,
)
def process_sla_reminders() -> int:
    """Evaluates SLA stages for pending verification and decision tasks (UC-SPACS-024)."""
    from modules.spacs.services.sla import process_pending_tasks_sla

    count = process_pending_tasks_sla()
    if count:
        log.info("spacs.sla.reminders_processed count=%d", count)
    return count


@shared_task(
    name="spacs.process_renewal_reminders",
    acks_late=True, reject_on_worker_lost=True,
    soft_time_limit=270, time_limit=300,
)
def process_renewal_reminders() -> int:
    """Issues reminders to eligible past scholarship recipients before renewal deadline (UC-SPACS-025)."""
    from modules.spacs.services.sla import process_scholarship_renewal_reminders

    count = process_scholarship_renewal_reminders()
    if count:
        log.info("spacs.renewal.reminders_processed count=%d", count)
    return count
