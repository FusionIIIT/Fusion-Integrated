"""Celery tasks for Complaint Management System."""
from __future__ import annotations

import logging
from celery import shared_task

log = logging.getLogger("fusion.complaints.tasks")


@shared_task(
    name="complaints.check_and_escalate_sla_breaches",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def check_and_escalate_sla_breaches() -> int:
    """UC-CMS-022 / BR-CMS-029: Automatically escalate unresolved complaints exceeding SLA deadline."""
    from modules.complaints.services import complaints as complaint_services

    count = complaint_services.check_and_escalate_sla_breaches()
    if count:
        log.info("complaints.sla.escalated count=%d", count)
    return count


@shared_task(
    name="complaints.check_and_send_sla_reminders",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def check_and_send_sla_reminders() -> int:
    """UC-CMS-021 / BR-CMS-028: Trigger pre-breach SLA reminder at 75% elapsed duration."""
    from modules.complaints.services import complaints as complaint_services

    count = complaint_services.check_and_send_sla_reminders()
    if count:
        log.info("complaints.sla.reminders_sent count=%d", count)
    return count
