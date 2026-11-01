"""Celery background tasks for PMS deadline monitoring and auto-expiration."""

from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

from modules.pms.domain.constants import STATUS_EXPIRED, STATUS_NEEDS_REVISION
from modules.pms.models import PatentApplication
from modules.pms.services.audit import record_audit_event
from modules.pms.services.deadlines import evaluate_deadlines_and_alerts

log = logging.getLogger("fusion.pms.tasks")


@shared_task(name="pms.evaluate_deadlines")
def evaluate_deadlines() -> dict[str, int]:
    """Periodic task: sweep deadlines to emit 30d, 15d, 5d alerts and escalate overdue items."""
    log.info("Running PMS deadline evaluation sweep.")
    results = evaluate_deadlines_and_alerts()
    log.info("PMS deadline evaluation completed: %s", results)
    return results


@shared_task(name="pms.expire_overdue_revisions")
def expire_overdue_revisions() -> int:
    """Expire applications breaching 60-day revision deadline (BR-PMS-035, 038)."""
    now = timezone.now()
    overdue_apps = PatentApplication.objects.filter(
        status=STATUS_NEEDS_REVISION,
        revision_deadline__lt=now,
    )
    count = 0
    for app in overdue_apps:
        prev_status = app.status
        app.status = STATUS_EXPIRED
        app.save()
        count += 1
        record_audit_event(
            application=app,
            user_id=0,
            actor_role="system",
            action_type="auto_expire_revision",
            previous_state=prev_status,
            new_state=STATUS_EXPIRED,
            details={"expired_at": now.isoformat()},
        )
    log.info("Expired %d overdue revision applications.", count)
    return count
