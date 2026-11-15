"""Workflow task selectors for ELM."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.elm.models import WorkflowTask


def get_pending_tasks_for_user(user_id: int) -> QuerySet[WorkflowTask]:
    """Return all pending actionable workflow tasks for an assigned user."""
    return WorkflowTask.objects.filter(
        assigned_to_user_id=user_id, status="pending"
    ).select_related("leave_application").order_by("created_at")


def get_task_by_id(task_id: int) -> WorkflowTask | None:
    return WorkflowTask.objects.filter(id=task_id).first()


def get_tasks_for_application(application_id: int) -> list[WorkflowTask]:
    return list(
        WorkflowTask.objects.filter(leave_application_id=application_id).order_by("created_at")
    )
