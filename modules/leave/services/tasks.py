"""Opening, completing and abandoning the work on a leave request.

Every state change goes through a task: the task is what names the person who
must act and what carries the SLA clock, so no state can be reached without
someone being answerable for it (BR-EL-032, BR-EL-033).
"""
from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from modules.leave.models import ApprovalTask, SlaThreshold
from modules.leave.models.requests import (
    TASK_CANCELLED,
    TASK_COMPLETED,
    TASK_PENDING,
)


def threshold_for(kind: str) -> SlaThreshold | None:
    return SlaThreshold.objects.filter(task_kind=kind, is_active=True).first()


def _due_at(now, hours: int | None):
    return None if hours is None else now + timedelta(hours=hours)


def open_task(*, leave_request, subject_type: str, subject_id: int, kind: str,
              assignee_user_id: int, now=None) -> ApprovalTask:
    """Assign work. Re-opening a kind supersedes any task left pending on it, so
    a re-submission cannot leave two live tasks for one step."""
    now = now or timezone.now()
    with transaction.atomic():
        ApprovalTask.objects.filter(
            subject_type=subject_type, subject_id=subject_id, kind=kind,
            status=TASK_PENDING).update(status=TASK_CANCELLED,
                                       updated_at=now)
        sla = threshold_for(kind)
        return ApprovalTask.objects.create(
            leave_request=leave_request, subject_type=subject_type,
            subject_id=subject_id, kind=kind, assignee_user_id=assignee_user_id,
            status=TASK_PENDING, assigned_at=now,
            reminder_due_at=_due_at(now, sla.reminder_hours if sla else None),
            escalation_due_at=_due_at(now, sla.escalate_hours if sla else None),
        )


def complete_task(task: ApprovalTask, *, outcome: str = "", note: str = "",
                  now=None) -> ApprovalTask:
    now = now or timezone.now()
    ApprovalTask.objects.filter(pk=task.pk).update(
        status=TASK_COMPLETED, completed_at=now, outcome=outcome, note=note,
        updated_at=now)
    task.status = TASK_COMPLETED
    task.completed_at = now
    task.outcome = outcome
    task.note = note
    return task


def cancel_open_tasks(*, subject_type: str, subject_id: int,
                      kinds: tuple[str, ...] | None = None,
                      now=None) -> int:
    """Close outstanding work because the thing it was about no longer applies."""
    qs = ApprovalTask.objects.filter(subject_type=subject_type, subject_id=subject_id,
                                     status=TASK_PENDING)
    if kinds:
        qs = qs.filter(kind__in=kinds)
    return qs.update(status=TASK_CANCELLED, updated_at=now or timezone.now())


def pending_task(*, subject_type: str, subject_id: int, kind: str
                 ) -> ApprovalTask | None:
    return ApprovalTask.objects.filter(
        subject_type=subject_type, subject_id=subject_id, kind=kind,
        status=TASK_PENDING).first()


def reassign(task: ApprovalTask, assignee_user_id: int) -> ApprovalTask:
    """SLA escalation that also moves responsibility (XTP-EL-01)."""
    ApprovalTask.objects.filter(pk=task.pk).update(
        assignee_user_id=assignee_user_id, escalated_to_user_id=assignee_user_id,
        updated_at=timezone.now())
    task.assignee_user_id = assignee_user_id
    task.escalated_to_user_id = assignee_user_id
    return task