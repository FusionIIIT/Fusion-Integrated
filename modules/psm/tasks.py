# Idempotent Celery tasks for PSM SLA sweeps, scheduled reports, and notifications.
from __future__ import annotations

from celery import shared_task

from modules.psm.services import approvals, common, reports


@shared_task(name="psm.check_approval_slas", acks_late=True, reject_on_worker_lost=True)
def check_approval_slas() -> dict[str, int]:
    """Emit idempotent SLA reminders and escalations for pending indents (BR-PSM-014)."""
    return approvals.sweep_slas()


@shared_task(name="psm.run_scheduled_reports", acks_late=True, reject_on_worker_lost=True)
def run_scheduled_reports() -> int:
    """Run all due active scheduled report definitions (PSM-UC-035)."""
    return reports.run_due_schedules()


@shared_task(name="psm.deliver_notifications", acks_late=True, reject_on_worker_lost=True)
def deliver_notifications() -> int:
    """Deliver queued PSM lifecycle notifications idempotently (BR-PSM-006)."""
    return common.deliver_pending_notifications()
