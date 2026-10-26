"""Actionable workflow task lifecycle for ELM.

A `WorkflowTask` row is opened whenever an application lands in a stage that
waits on a human, and closed when that stage is left. Every open carries a
BR-EL-035 assignment notification.

Why a table at all: SLA processing (BR-EL-032/033) needs the moment a task
landed on its *current* assignee and whether a reminder or escalation has
already been issued for it. Neither is recoverable from `LeaveApplication`
alone -- `updated_at` moves on every unrelated field write, and there is
nowhere to record "already reminded".
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from modules.elm.domain.sla import TaskKind
from modules.elm.models import WorkflowTask
from modules.elm.services.notifications import application_ref, notify_task_assigned

#: Application status -> (task kind, attribute holding the assignee id).
#: Statuses absent from this map are terminal or need no human action, so no
#: task is opened for them.
STATUS_TASK_MAP: dict[str, tuple[TaskKind, str]] = {
    "AWAITING_SUBSTITUTE": (TaskKind.SUBSTITUTE_RESPONSE, "substitute_id"),
    "AWAITING_UNIT_HEAD": (TaskKind.UNIT_HEAD_REVIEW, "unit_head_id"),
    "AWAITING_ESTABLISHMENT": (TaskKind.ESTABLISHMENT_ROUTING, "establishment_id"),
    "AWAITING_SANCTION": (TaskKind.SANCTION_DECISION, "sanctioning_authority_id"),
    "AWAITING_DIRECTOR_SELF_SANCTION": (TaskKind.DIRECTOR_SELF_SANCTION, "employee_id"),
    "APPLICANT_ACTION_REQUIRED": (TaskKind.UNIT_HEAD_REVIEW, "employee_id"),
}


def open_task(
    task_kind: str | TaskKind,
    assignee_id: int | None,
    application=None,
    subject_type: str = "APPLICATION",
    subject_id: int | None = None,
    applicant_name: str = "",
    notify: bool = True,
) -> WorkflowTask | None:
    """Open an actionable task and notify its assignee (BR-EL-035).

    Returns None when there is no assignee: an unowned queue is a legitimate
    intermediate state and must not break the enclosing transition.
    """
    if not assignee_id:
        return None

    kind_value = TaskKind(task_kind).value if _known(task_kind) else str(task_kind)

    task = WorkflowTask.objects.create(
        application=application,
        subject_type=subject_type,
        subject_id=subject_id if subject_id is not None else (application.id if application else None),
        task_kind=kind_value,
        assignee_id=assignee_id,
        status=WorkflowTask.STATUS_OPEN,
        opened_at=timezone.now(),
    )

    if notify:
        notify_task_assigned(
            recipient_id=assignee_id,
            task_kind=kind_value,
            application_ref=application_ref(application),
            applicant_name=applicant_name,
            task_id=task.id,
        )
    return task


def close_open_tasks(
    application=None,
    subject_type: str = "APPLICATION",
    subject_id: int | None = None,
    task_kind: str | TaskKind | None = None,
    closed_by_id: int | None = None,
    reason: str = "stage_completed",
) -> int:
    """Close the open tasks for a subject. Returns how many were closed.

    Closing is what makes the pending-only guard real: once this has run, an
    SLA threshold crossed later for the same task yields no reminder and no
    escalation (BR-EL-032, BR-EL-033).

    The update is a single queryset UPDATE, so a task cannot be closed twice by
    two concurrent transitions -- the second matches zero rows.
    """
    qs = WorkflowTask.objects.filter(status=WorkflowTask.STATUS_OPEN)

    if application is not None:
        qs = qs.filter(application=application)
    elif subject_id is not None:
        qs = qs.filter(subject_type=subject_type, subject_id=subject_id)
    else:
        return 0

    if task_kind is not None:
        qs = qs.filter(task_kind=TaskKind(task_kind).value if _known(task_kind) else str(task_kind))

    return qs.update(
        status=WorkflowTask.STATUS_CLOSED,
        closed_at=timezone.now(),
        closed_by_id=closed_by_id,
        closed_reason=reason[:64],
        updated_at=timezone.now(),
    )


def advance_application_task(
    application,
    actor_id: int | None = None,
    applicant_name: str = "",
    reason: str = "stage_completed",
) -> WorkflowTask | None:
    """Close the tasks for an application's previous stage and open the next.

    Called by every service that moves an application between statuses, so
    exactly one open task exists per live application stage. Terminal statuses
    close the outstanding tasks and open nothing.
    """
    with transaction.atomic():
        close_open_tasks(
            application=application,
            closed_by_id=actor_id,
            reason=reason,
        )

        mapping = STATUS_TASK_MAP.get(application.status)
        if mapping is None:
            return None

        task_kind, assignee_attr = mapping
        assignee_id = getattr(application, assignee_attr, None)
        return open_task(
            task_kind=task_kind,
            assignee_id=assignee_id,
            application=application,
            applicant_name=applicant_name,
        )


def _known(kind) -> bool:
    try:
        TaskKind(kind)
    except ValueError:
        return False
    return True
