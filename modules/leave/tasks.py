"""Scheduled ELM event handlers."""
from celery import shared_task
from datetime import timedelta
from django.db import transaction
from django.utils import timezone

from modules.leave.models import LeaveAuditEvent, LeavePolicy, LeaveSLAConfiguration, WorkflowTask
from modules.leave.services.accounting import process_year_end
from modules.leave.services.notifications import deliver_pending, enqueue
from modules.leave.domain.state_machine import normalize_role


@shared_task(name="leave.process_configured_year_end")
def process_configured_year_end():
    """Run the configured annual close once on its configured date."""
    today = timezone.localdate()
    policy = LeavePolicy.objects.filter(policy_key="current").first()
    if not policy or (today.month, today.day) != (policy.year_end_month, policy.year_end_day):
        return {"processed": False}
    result = process_year_end(today.year)
    return {"processed": True, **result}


@shared_task(name="leave.deliver_notifications")
def deliver_leave_notifications():
    return deliver_pending()


@shared_task(name="leave.process_sla_thresholds")
def process_leave_sla_thresholds():
    """Remind or escalate only tasks that remain pending at each threshold."""
    now = timezone.now()
    counts = {"reminded": 0, "escalated": 0}
    ids = list(WorkflowTask.objects.filter(state=WorkflowTask.State.PENDING).values_list("id", flat=True))
    for task_id in ids:
        with transaction.atomic():
            task = (WorkflowTask.objects.select_for_update().select_related("request")
                    .filter(pk=task_id, state=WorkflowTask.State.PENDING).first())
            if not task:
                continue
            config, _ = LeaveSLAConfiguration.objects.get_or_create(role=task.role)
            activated = task.activated_at or task.created_at
            age = now - activated
            if task.reminder_sent_at is None and age >= timedelta(hours=config.reminder_after_hours):
                enqueue(
                    recipient_user_id=task.assigned_user_id, topic="task.reminder",
                    dedupe_key=f"task:{task.pk}:reminder",
                    subject="Reminder: ELM action is still pending",
                    body=f"Leave request #{task.request_id} is still waiting for your {task.role.replace('_', ' ')} action.",
                    payload={"task_id": task.pk, "request_id": task.request_id},
                )
                task.reminder_sent_at = now
                task.save(update_fields=["reminder_sent_at"])
                LeaveAuditEvent.objects.create(request=task.request, action="sla_reminder",
                                               from_status=task.request.status, to_status=task.request.status,
                                               details={"task_id": task.pk, "role": task.role})
                counts["reminded"] += 1
            if task.escalated_at is None and age >= timedelta(hours=config.escalate_after_hours):
                old_role = task.role
                recipient = config.escalation_user_id or task.assigned_user_id
                enqueue(
                    recipient_user_id=recipient, topic="task.escalation",
                    dedupe_key=f"task:{task.pk}:escalation",
                    subject="Escalation: ELM action remains pending",
                    body=f"Leave request #{task.request_id} remains pending beyond the configured escalation threshold.",
                    payload={"task_id": task.pk, "request_id": task.request_id, "role": old_role},
                )
                if config.escalation_user_id:
                    task.assigned_user_id = config.escalation_user_id
                if config.escalation_role:
                    task.role = normalize_role(config.escalation_role)
                task.escalated_at = now
                task.save(update_fields=["assigned_user_id", "role", "escalated_at"])
                LeaveAuditEvent.objects.create(request=task.request, action="sla_escalated",
                                               from_status=task.request.status, to_status=task.request.status,
                                               details={"task_id": task.pk, "from_role": old_role,
                                                        "to_role": task.role,
                                                        "recipient_user_id": recipient})
                counts["escalated"] += 1
    return counts
