"""SLA reminder and escalation (SF-EL-002, BR-EL-032, BR-EL-033, WF-EL-08)."""
from __future__ import annotations

from django.utils import timezone

from modules.leave.models import WorkflowTask
from modules.leave.services import notifications


def process_due(now=None) -> dict:
    now = now or timezone.now()
    reminded = 0
    escalated = 0
    skipped = 0
    pending = WorkflowTask.objects.filter(status="pending", sla_controlled=True)
    for task in pending:
        still_pending = task.status == "pending"
        if not still_pending:
            skipped += 1
            continue
        if task.reminder_at and now >= task.reminder_at and task.reminded_at is None:
            if task.assignee_user_id:
                notifications.notify_user(
                    task.assignee_user_id, topic="leave.sla.reminder",
                    key=f"leave.sla.reminder:{task.pk}",
                    subject="Leave task reminder",
                    body=f"A {task.kind} task is still pending.",
                )
            task.reminded_at = now
            task.save(update_fields=["reminded_at"])
            reminded += 1
        if task.escalate_at and now >= task.escalate_at and task.escalated_at is None:
            notifications.enqueue(
                topic="leave.sla.escalation",
                dedupe_key=f"leave.sla.escalation:{task.pk}",
                subject="Leave task escalation",
                body=f"A {task.kind} task exceeded its escalation threshold.",
                recipient_email="leave-escalation@invalid",
                payload={"task_id": task.pk, "application_id": task.application_id,
                         "assignee_role": task.assignee_role},
            )
            task.escalated_at = now
            task.save(update_fields=["escalated_at"])
            escalated += 1
    return {"reminded": reminded, "escalated": escalated, "skipped": skipped}
