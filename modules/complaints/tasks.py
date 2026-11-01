"""Scheduled background tasks for Complaint Management System."""
from __future__ import annotations

import logging
from celery import shared_task

log = logging.getLogger("fusion.complaints.tasks")


@shared_task(
    name="complaints.run_sla_sweep",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def run_sla_sweep() -> str:
    """Check SLA thresholds, trigger pre-breach reminders and auto-escalate breaches."""
    from modules.complaints.services import complaints as svc

    reminders = svc.send_sla_reminders()
    escalations = svc.escalate_automatic_sla()
    summary = f"SLA sweep completed: {reminders} reminders, {escalations} automatic escalations."
    log.info(summary)
    return summary

