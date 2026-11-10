"""SPACS Task Routing, SLA Escalation, and Role Reassignment Service."""

from datetime import timedelta
from django.utils import timezone

from ..models import SpacsTask
from ..domain.rules import is_sla_breached
from .audit import log_action
from .audit import notify_user


def create_task(
    task_type: str,
    entity_type: str,
    entity_id: str,
    assigned_role: str,
    assigned_user_id: int | None = None,
    sla_hours: int = 48,
) -> SpacsTask:
    """Create a task routed to a SPACS role or specific actor."""
    due_at = timezone.now() + timedelta(hours=sla_hours)
    return SpacsTask.objects.create(
        task_type=task_type,
        entity_type=entity_type,
        entity_id=str(entity_id),
        assigned_role=assigned_role,
        assigned_user_id=assigned_user_id,
        status="pending",
        due_at=due_at,
    )


def close_pending_tasks(entity_type: str, entity_id: str) -> int:
    """Mark all pending tasks for this entity as completed/cancelled."""
    return SpacsTask.objects.filter(
        entity_type=entity_type,
        entity_id=str(entity_id),
        status="pending",
    ).update(status="completed")


def check_and_escalate_sla_tasks(sla_hours: int = 48) -> list[SpacsTask]:
    """Issue configured reminders/escalations when tasks exceed their SLA threshold (AFR-SPACS-026, BR-SPACS-013)."""
    now = timezone.now()
    pending_tasks = SpacsTask.objects.filter(status="pending")
    escalated = []

    for task in pending_tasks:
        if is_sla_breached(task.created_at, sla_hours, now):
            escalated.append(task)
            if task.assigned_user_id:
                notify_user(
                    recipient_user_id=task.assigned_user_id,
                    event_type="sla_reminder",
                    title="SLA Escalation Notice",
                    message=f"Task {task.task_type} for {task.entity_type} {task.entity_id} has exceeded its SLA threshold.",
                )
            log_action(
                event_type="task_sla_escalated",
                entity_type="task",
                entity_id=str(task.id),
                actor_user_id=1,  # System
                details={"task_type": task.task_type, "assigned_role": task.assigned_role},
            )
    return escalated


def reassign_role_tasks(
    assigned_role: str,
    old_user_id: int,
    new_user_id: int,
    acting_user_id: int,
) -> int:
    """Route pending tasks to the new role holder while preserving past completed history (AFR-SPACS-052, BR-SPACS-022)."""
    updated_count = SpacsTask.objects.filter(
        assigned_role=assigned_role,
        assigned_user_id=old_user_id,
        status="pending",
    ).update(assigned_user_id=new_user_id)

    log_action(
        event_type="role_tasks_reassigned",
        entity_type="role_reassignment",
        entity_id=assigned_role,
        actor_user_id=acting_user_id,
        details={
            "old_user_id": old_user_id,
            "new_user_id": new_user_id,
            "reassigned_tasks_count": updated_count,
        },
    )
    return updated_count
