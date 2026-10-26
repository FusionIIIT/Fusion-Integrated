"""Read queries for SLA configuration, workflow tasks and notifications.

Ownership scoping lives here, not in the views: a selector that cannot be
called without a user id is harder to misuse than a view that remembers to
filter (BR-EL-036).
"""
from __future__ import annotations

from django.db.models import QuerySet

from modules.elm.models import Notification, SLAConfiguration, SLAEventLog, WorkflowTask


def list_sla_configurations() -> QuerySet[SLAConfiguration]:
    """Every configured task kind, for the administration screen (EL-UC-018)."""
    return SLAConfiguration.objects.all().order_by("task_kind")


def get_sla_configuration(task_kind: str) -> SLAConfiguration | None:
    return SLAConfiguration.objects.filter(task_kind=task_kind).first()


def get_open_tasks_for_user(user_id: int) -> QuerySet[WorkflowTask]:
    """A user's own open actionable tasks."""
    return (
        WorkflowTask.objects.filter(assignee_id=user_id, status=WorkflowTask.STATUS_OPEN)
        .select_related("application", "application__leave_type")
        .order_by("opened_at")
    )


def get_overdue_tasks(task_kind: str | None = None) -> QuerySet[WorkflowTask]:
    """Open tasks that have already been escalated, for an admin overview."""
    qs = WorkflowTask.objects.filter(
        status=WorkflowTask.STATUS_OPEN, escalated_at__isnull=False
    ).select_related("application", "application__leave_type")
    if task_kind:
        qs = qs.filter(task_kind=task_kind)
    return qs.order_by("opened_at")


def get_user_notifications(user_id: int, unread_only: bool = False, limit: int = 50):
    """A user's notifications, newest first, scoped to that user.

    Sliced in the query so a long-lived account does not stream its whole
    history into a response.
    """
    qs = Notification.objects.filter(recipient_id=user_id)
    if unread_only:
        qs = qs.filter(read_at__isnull=True)
    return qs.order_by("-created_at")[:limit]


def count_unread_notifications(user_id: int) -> int:
    return Notification.objects.filter(recipient_id=user_id, read_at__isnull=True).count()


def get_sla_event_log(task_id: int | None = None, limit: int = 100):
    """SLA evaluation log, including suppressed evaluations (EL-UC-021 audit)."""
    qs = SLAEventLog.objects.all()
    if task_id is not None:
        qs = qs.filter(task_id=task_id)
    return qs.order_by("-evaluated_at")[:limit]
