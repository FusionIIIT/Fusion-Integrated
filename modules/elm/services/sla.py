"""SLA reminders and escalations for stale workflow tasks (BR-EL-032/033)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from modules.elm.models import SlaEvent, WorkflowTask
from modules.elm.services import config, notifications


@dataclass
class SlaReport:
    reminded: int = 0
    escalated: int = 0

    def __str__(self) -> str:
        return f"reminded={self.reminded} escalated={self.escalated}"


def _age(now, task) -> timedelta:
    return now - task.created_at


@transaction.atomic
def process(*, now=None) -> SlaReport:
    now = now or timezone.now()
    report = SlaReport()
    tasks = (WorkflowTask.objects
             .filter(status="pending")
             .select_related("request"))
    for task in tasks:
        cfg = config.sla_for(task.task_type)
        if not cfg.active:
            continue
        age = _age(now, task)
        if (task.reminder_sent_at is None and cfg.reminder_hours
                and age >= timedelta(hours=cfg.reminder_hours)):
            _remind(task, actor_user_id=None, now=now)
            report.reminded += 1
        if (task.escalated_at is None and cfg.escalation_hours
                and age >= timedelta(hours=cfg.escalation_hours)):
            _escalate(task, cfg=cfg, actor_user_id=None, now=now)
            report.escalated += 1
    return report


def _remind(task: WorkflowTask, *, actor_user_id: int | None, now) -> None:
    task.reminder_sent_at = now
    task.save(update_fields=["reminder_sent_at", "updated_at"])
    SlaEvent.objects.create(task=task, kind="reminder", note="SLA reminder",
                            actor_user_id=actor_user_id)
    if task.assigned_to_user_id:
        notifications.enqueue(
            topic="sla.reminder",
            dedupe_key=f"sla:remind:task{task.pk}",
            subject=f"Reminder: leave request #{task.request_id} is waiting",
            body=f"A {task.task_type} step has been pending beyond the SLA.",
            recipient_user_id=task.assigned_to_user_id,
            payload={"request_id": task.request_id, "task_id": task.pk})


def _escalate(task: WorkflowTask, *, cfg, actor_user_id: int | None, now) -> None:
    task.escalated_at = now
    task.save(update_fields=["escalated_at", "updated_at"])
    SlaEvent.objects.create(task=task, kind="escalation",
                            note=f"Escalated to {cfg.escalate_to_designation}",
                            actor_user_id=actor_user_id)
    notifications.enqueue(
        topic="sla.escalation",
        dedupe_key=f"sla:escalate:task{task.pk}",
        subject=f"Escalation: leave request #{task.request_id} overdue",
        body=(f"A {task.task_type} step was not actioned within the SLA and has "
              f"been escalated to {cfg.escalate_to_designation or 'the authority'}."),
        recipient_user_id=task.request.user_id,
        payload={"request_id": task.request_id, "task_id": task.pk})
