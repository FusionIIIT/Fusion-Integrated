"""The SLA clock: reminders and escalations (BR-EL-032, BR-EL-033, XTP-EL-01).

A threshold is data, not code. `escalation_changes_routing` decides whether an
escalation merely notifies a higher authority or also moves responsibility for
the outstanding task.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.utils import timezone

from modules.leave.models import SlaThreshold
from modules.leave.services import notifications
from modules.leave.selectors import queries

log = logging.getLogger("fusion.leave.sla")


def remind(*, now=None) -> int:
    """Nudge every task whose reminder threshold has passed."""
    now = now or timezone.now()
    sent = 0
    for task in queries.reminders_due(now=now):
        sent += _mark_reminded(task, now)
    if sent:
        log.info("leave.sla.reminded count=%d", sent)
    return sent


def escalate(*, now=None) -> int:
    """Escalate every task whose escalation threshold has passed."""
    now = now or timezone.now()
    count = 0
    for task in queries.escalations_due(now=now):
        count += _escalate(task, now=now)
    if count:
        log.info("leave.sla.escalated count=%d", count)
    return count


def _mark_reminded(task, now) -> int:
    from modules.leave.models import ApprovalTask

    # Claim it with a conditional update, so two workers send one reminder.
    if not ApprovalTask.objects.filter(
            pk=task.pk, reminder_sent_at__isnull=True).update(
            reminder_sent_at=now, updated_at=now):
        return 0
    request = task.leave_request
    notifications.enqueue(
        topic="leave.sla.reminder",
        dedupe_key=f"sla-reminder:{task.pk}",
        recipient_user_id=task.assignee_user_id,
        subject="A leave request is waiting for you",
        body=f"Request #{request.pk} has been awaiting your decision since "
             f"{task.assigned_at:%Y-%m-%d %H:%M}.")
    return 1


def _escalate(task, now) -> int:
    from modules.leave.models import ApprovalTask
    from modules.leave.services import tasks as task_service

    sla = SlaThreshold.objects.filter(task_kind=task.kind, is_active=True).first()
    if sla is None or sla.escalate_hours is None:
        return 0
    if not ApprovalTask.objects.filter(
            pk=task.pk, escalated_at__isnull=True).update(
            escalated_at=now, updated_at=now):
        return 0

    target = sla.escalation_user_id
    designation = sla.escalation_designation or "the higher authority"
    if target is not None:
        notifications.enqueue(
            topic="leave.sla.escalation",
            dedupe_key=f"sla-escalation:{task.pk}",
            recipient_user_id=target,
            subject="A leave request has been escalated",
            body=f"Request #{task.leave_request_id} has waited for "
                 f"{task.assignee_user_id} since {task.assigned_at:%Y-%m-%d}.")
    if sla.escalation_changes_routing and target is not None:
        task_service.reassign(task, target)
        log.info("leave.sla.reassigned task=%s to=%s", task.pk, target)
    else:
        log.info("leave.sla.escalated task=%s after=%s to=%s designation=%s",
                 task.pk, timedelta(hours=sla.escalate_hours), target, designation)
    return 1


class _AdminView:
    """Read-only stand-in, so the exception screen's totals can see every task
    without a request. It grants only what the screen reads."""

    permissions = frozenset({"leave.record.maintain"})

    def __init__(self) -> None:
        self.user_id = None

    def has_permission(self, code: str) -> bool:
        return code in self.permissions

    def has_any_permission(self, *codes: str) -> bool:
        return any(c in self.permissions for c in codes)


_ADMIN_VIEW = _AdminView()


def overdue_overview(*, today=None) -> dict[str, int]:
    """What the exception screen shows (BR-EL-032): what is waiting to fire and
    which pending tasks are behind."""
    today = today or timezone.now().date()
    now = timezone.now()
    return {
        "reminders_due": queries.reminders_due(now=now).count(),
        "escalations_due": queries.escalations_due(now=now).count(),
        "pending_tasks": sum(queries.open_task_counts(_ADMIN_VIEW).values()),
        "overdue_out_of_office": queries.overdue_out_of_office(
            _ADMIN_VIEW, today=today).count(),
    }