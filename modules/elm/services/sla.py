"""Pending-only SLA reminders and escalation notifications."""
from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from modules.elm.models import LeavePolicy, WorkflowTask
from modules.elm.services.notifications import enqueue


def process_sla_thresholds(*, now=None, limit: int = 500) -> dict[str, int]:
    now = now or timezone.now()
    tasks = (WorkflowTask.objects.filter(status="pending")
             .select_related("request").order_by("assigned_at", "pk")[:limit])
    report = {"reminded": 0, "escalated": 0, "skipped": 0}
    for candidate in tasks:
        with transaction.atomic():
            task = (WorkflowTask.objects.select_for_update()
                    .select_related("request")
                    .filter(pk=candidate.pk, status="pending").first())
            if task is None:
                report["skipped"] += 1
                continue
            policy = LeavePolicy.objects.filter(
                year=task.request.starts_on.year).first()
            if policy is None:
                report["skipped"] += 1
                continue
            age = now - task.assigned_at
            if (task.reminder_sent_at is None
                    and age >= timedelta(hours=policy.reminder_after_hours)):
                enqueue(
                    topic="task_reminder",
                    dedupe_key=f"task:{task.pk}:reminder",
                    recipient_user_id=task.assigned_user_id,
                    subject=f"ELM approval reminder: request {task.request_id}",
                    body=(f"Leave request {task.request_id} is awaiting your "
                          f"decision in the {task.role} step."))
                task.reminder_sent_at = now
                task.save(update_fields=("reminder_sent_at", "updated_at"))
                task.request.events.create(
                    actor_user_id=None, event="sla_reminder",
                    from_status=task.request.status,
                    to_status=task.request.status,
                    note=f"Reminder issued for pending task {task.pk}.")
                report["reminded"] += 1

            if (task.escalation_sent_at is None
                    and age >= timedelta(hours=policy.escalate_after_hours)):
                next_task = task.request.tasks.filter(
                    status="waiting").order_by("sequence").first()
                recipient_id = (
                    policy.escalation_user_id if policy.escalation_user_id
                    else next_task.assigned_user_id if next_task
                    else task.assigned_user_id)
                enqueue(
                    topic="task_escalation",
                    dedupe_key=f"task:{task.pk}:escalation",
                    recipient_user_id=recipient_id,
                    subject=f"ELM approval escalation: request {task.request_id}",
                    body=(f"Leave request {task.request_id} remains pending "
                          f"with {task.role}. Please follow up."))
                task.escalation_sent_at = now
                task.save(update_fields=("escalation_sent_at", "updated_at"))
                task.request.events.create(
                    actor_user_id=None, event="sla_escalation",
                    from_status=task.request.status,
                    to_status=task.request.status,
                    note=(f"Escalation issued for pending task {task.pk} "
                          f"to user {recipient_id}."))
                report["escalated"] += 1
    return report
