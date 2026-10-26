"""EL-UC-021: remind and escalate still-pending tasks, logging each (BR-EL-032/033)."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.utils import timezone

from modules.leave.domain import sla as sla_domain
from modules.leave.domain import state_machine as sm
from modules.leave.models import RequestEvent, SlaEvent, Task
from modules.leave.services import configuration, notifications

log = logging.getLogger("fusion.leave.sla")


@dataclass
class SlaReport:
    reminded: int = 0
    escalated: int = 0
    reassigned: int = 0

    def __str__(self) -> str:
        return f"reminded={self.reminded} escalated={self.escalated} reassigned={self.reassigned}"


def process(now=None) -> SlaReport:
    now = now or timezone.now()
    rules = configuration.current_sla()
    report = SlaReport()
    if not rules:
        return report
    candidates = (Task.objects.filter(status=Task.OPEN, step__in=list(rules))
                  .values_list("pk", flat=True))
    for task_id in list(candidates):
        _one(task_id, rules, now, report)
    log.info("leave.sla %s", report)
    return report


@transaction.atomic
def _one(task_id: int, rules, now, report: SlaReport) -> None:
    task = (Task.objects.select_for_update(skip_locked=True).select_related("request")
            .filter(pk=task_id).first())
    if task is None or task.status != Task.OPEN:
        return
    rule = rules[task.step]
    action = sla_domain.due(rule, opened_at=task.opened_at, now=now,
                            reminded=task.reminded_at is not None,
                            escalated=task.escalated_at is not None)
    if action == sla_domain.NOTHING:
        return
    req = task.request
    if action == sla_domain.REMIND:
        if not _log(task, "remind", "", task.assignee_designation, ""):
            return
        task.reminded_at = now
        task.save(update_fields=["reminded_at"])
        notifications.enqueue(
            topic="sla.reminder", dedupe_key=f"remind:{task.pk}", user_id=task.assignee_user_id,
            designation="" if task.assignee_user_id else task.assignee_designation,
            subject=f"Reminder: leave request #{req.pk} is waiting for you",
            body=f"Leave request #{req.pk} has waited {rule.reminder_hours} hour(s) for your "
                 f"action.")
        report.reminded += 1
        return
    target = rule.escalate_to
    if not _log(task, "escalate", rule.action, task.assignee_designation, target):
        return
    task.escalated_at = now
    if rule.action == sla_domain.REASSIGN and target:
        previous = task.assignee_designation
        task.assignee_designation = target
        task.save(update_fields=["escalated_at", "assignee_designation"])
        RequestEvent.objects.create(request=req, event="sla_reassigned", from_status=req.status,
                                    to_status=req.status, actor_role="system",
                                    remarks=f"Reassigned from {previous} to {target}")
        notifications.enqueue(
            topic="task.assigned", dedupe_key=f"task:{task.pk}:{target}", designation=target,
            subject=f"Leave request #{req.pk} was escalated to you",
            body=f"Leave request #{req.pk} waited past its deadline with {previous} and is now "
                 f"in your queue.")
        report.reassigned += 1
    else:
        task.save(update_fields=["escalated_at"])
        notifications.enqueue(
            topic="sla.escalated", dedupe_key=f"escalate:{task.pk}",
            user_id=req.user_id if task.step == sm.SUBSTITUTE and not target else None,
            designation=target,
            subject=f"Leave request #{req.pk} is overdue",
            body=f"Leave request #{req.pk} has waited {rule.escalation_hours} hour(s) at the "
                 f"{task.step.replace('_', ' ')} step without action.")
    report.escalated += 1


def _log(task: Task, kind: str, action: str, frm: str, to: str) -> bool:
    """The unique row is the guard: a second worker on the same tick does nothing."""
    try:
        with transaction.atomic():
            SlaEvent.objects.create(task=task, kind=kind, action=action, from_designation=frm,
                                    to_designation=to)
    except IntegrityError:
        return False
    return True
