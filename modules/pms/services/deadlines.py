"""Deadline monitoring, reminders (30d, 15d, 5d) and escalation sweep (BR-PMS-097..104)."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from modules.pms.models import DeadlineTracking
from modules.pms.services.audit import record_audit_event

log = logging.getLogger("fusion.pms.deadlines")


@transaction.atomic
def evaluate_deadlines_and_alerts() -> dict[str, int]:
    """Sweep active deadlines to trigger 30, 15, and 5-day notifications and escalations.

    Implemented as a testable service, suitable for periodic Celery tasks or management commands.
    """
    now = timezone.now()
    active_deadlines = DeadlineTracking.objects.filter(resolved_at__isnull=True)

    alerts_30 = 0
    alerts_15 = 0
    alerts_5 = 0
    escalations = 0

    for dl in active_deadlines:
        time_left = dl.due_date - now

        # 30-day alert (BR-PMS-101)
        if timedelta(days=15) < time_left <= timedelta(days=30) and not dl.alert_30_sent:
            dl.alert_30_sent = True
            dl.save(update_fields=["alert_30_sent"])
            alerts_30 += 1
            record_audit_event(
                application=dl.application,
                user_id=0,
                actor_role="system",
                action_type="alert_30_days",
                details={"deadline_type": dl.deadline_type, "due_date": dl.due_date.isoformat()},
            )

        # 15-day alert (BR-PMS-102)
        elif timedelta(days=5) < time_left <= timedelta(days=15) and not dl.alert_15_sent:
            dl.alert_15_sent = True
            dl.save(update_fields=["alert_15_sent"])
            alerts_15 += 1
            record_audit_event(
                application=dl.application,
                user_id=0,
                actor_role="system",
                action_type="alert_15_days",
                details={"deadline_type": dl.deadline_type, "due_date": dl.due_date.isoformat()},
            )

        # 5-day urgent alert (BR-PMS-103)
        elif timedelta(days=0) <= time_left <= timedelta(days=5) and not dl.alert_5_sent:
            dl.alert_5_sent = True
            dl.save(update_fields=["alert_5_sent"])
            alerts_5 += 1
            record_audit_event(
                application=dl.application,
                user_id=0,
                actor_role="system",
                action_type="alert_5_days",
                details={"deadline_type": dl.deadline_type, "due_date": dl.due_date.isoformat()},
            )

        # Overdue escalation (BR-PMS-104)
        elif time_left < timedelta(seconds=0) and not dl.is_escalated:
            dl.is_escalated = True
            dl.escalated_at = now
            dl.save(update_fields=["is_escalated", "escalated_at"])
            escalations += 1
            record_audit_event(
                application=dl.application,
                user_id=0,
                actor_role="system",
                action_type="deadline_escalated",
                details={
                    "deadline_type": dl.deadline_type,
                    "overdue_since": dl.due_date.isoformat(),
                },
            )

    return {
        "alerts_30": alerts_30,
        "alerts_15": alerts_15,
        "alerts_5": alerts_5,
        "escalations": escalations,
    }
