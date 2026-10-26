"""Notification decisions.

Every notification is written in the same transaction as the decision that
caused it, so a row can never claim an approval that was rolled back.
`dedupe_key` makes a redelivered event idempotent.

The baseline is explicit about WHEN someone is told (BR-EL-032/033/035,
CFR-EL-016): a final decision reaches the employee, an assigned task reaches
whoever it was assigned to, a withdrawal reaches the roles that were still
working on it. Intermediate states deliberately do not — the employee reads
those from their own history.

The drain worker is not part of this change; rows accumulate in `pending` until
one exists (see the module doc's list of gaps).
"""
from __future__ import annotations

import logging

from django.db import IntegrityError, transaction

from modules.leave.models import LeaveNotification, LeaveRequest

log = logging.getLogger("fusion.leave.notify")

TOPICS = {
    "leave.task_assigned",
    "leave.substitute_requested",
    "leave.substitute_responded",
    "leave.decided",
    "leave.withdrawn",
    "leave.cancellation_decided",
    "leave.resumption_reviewed",
    "leave.reminder",
    "leave.escalated",
}


def notify(*, topic: str, dedupe_key: str, recipient_user_id: int,
           subject: str, body: str = "",
           request: LeaveRequest | None = None) -> LeaveNotification | None:
    """Queue one notification inside the caller's transaction. None if it was
    already queued — the key is what makes that safe."""
    if topic not in TOPICS:
        raise ValueError(f"Unknown leave notification topic {topic!r}.")
    try:
        # Nested, so a duplicate key cannot poison the caller's transaction.
        with transaction.atomic():
            return LeaveNotification.objects.create(
                topic=topic, dedupe_key=dedupe_key,
                recipient_user_id=recipient_user_id, subject=subject,
                body=body, request=request)
    except IntegrityError:
        log.debug("leave.notify.duplicate key=%s", dedupe_key)
        return None


def tell_the_employee(request: LeaveRequest, subject: str, body: str = "") -> None:
    notify(topic="leave.decided",
           dedupe_key=f"leave.decided:{request.pk}",
           recipient_user_id=request.user_id, subject=subject, body=body,
           request=request)


def tell_the_assignee(task, subject: str, body: str = "") -> None:
    if task.assignee_user_id is None:
        return
    notify(topic="leave.task_assigned",
           dedupe_key=f"leave.task:{task.pk}",
           recipient_user_id=task.assignee_user_id, subject=subject,
           body=body, request=task.request)


def tell_concerned_roles(request: LeaveRequest, subject: str) -> None:
    """Withdrawal reaches whoever was still holding a task (BR-EL-022)."""
    from modules.leave.models import LeaveTask

    assignees = set(LeaveTask.objects
                    .filter(request=request, status="pending")
                    .exclude(assignee_user_id=None)
                    .values_list("assignee_user_id", flat=True))
    for user_id in assignees:
        notify(topic="leave.withdrawn",
               dedupe_key=f"leave.withdrawn:{request.pk}:{user_id}",
               recipient_user_id=user_id, subject=subject, request=request)
