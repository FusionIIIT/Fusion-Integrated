"""The SLA sweep (EL-UC-021, EVT-02).

Two thresholds, one rule each, and the same guard on both: nothing is sent for
a task that is no longer pending (BR-EL-032/033). Because a stage that has been
passed supersedes its task in the same transaction, "still pending" is a query
rather than a hope.

Escalation is recorded on the task and routed to the one responsible person
this module can name for a request — its Unit Head — alongside whoever is
holding the task. Where the escalation configuration changes routing or
responsibility, that is a decision for the authority, not for a sweep.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from django.utils import timezone

from modules.leave.models import LeaveTask
from modules.leave.services import notifications

log = logging.getLogger("fusion.leave.sla")


@dataclass
class SweepReport:
    reminded: list[int] = field(default_factory=list)
    escalated: list[int] = field(default_factory=list)
    skipped: int = 0

    def __str__(self) -> str:
        return (f"{len(self.reminded)} reminded, {len(self.escalated)} "
                f"escalated, {self.skipped} already closed")


def sweep(*, now=None) -> SweepReport:
    """One pass over every pending task. Safe to run often and to re-run."""
    now = now or timezone.now()
    report = SweepReport()

    for task in (LeaveTask.objects.filter(status="pending")
                 .select_related("request")):
        due_for_reminder = (task.reminder_due_at is not None
                            and task.reminder_due_at <= now
                            and task.reminded_at is None)
        due_for_escalation = (task.escalation_due_at is not None
                              and task.escalation_due_at <= now
                              and task.escalated_at is None)
        if not (due_for_reminder or due_for_escalation):
            continue

        update = []
        if due_for_reminder:
            task.reminded_at = now
            update.append("reminded_at")
            report.reminded.append(task.pk)
            log.info("leave.sla.reminder task=%s stage=%s", task.pk, task.stage)
            _tell(task, "leave.reminder",
                  "Reminder: a leave request at the "
                  f"{task.stage} stage is still waiting.")
        if due_for_escalation:
            task.escalated_at = now
            update.append("escalated_at")
            report.escalated.append(task.pk)
            log.info("leave.sla.escalation task=%s stage=%s", task.pk, task.stage)
            _escalate(task)
        task.save(update_fields=[*update, "updated_at"])

    return report


def _tell(task, topic: str, body: str) -> None:
    """A reminder goes to whoever is holding the task."""
    if task.assignee_user_id is None:
        return
    notifications.notify(topic=topic, dedupe_key=f"{topic}:{task.pk}",
                         recipient_user_id=task.assignee_user_id,
                         subject=f"{topic.rsplit('.', maxsplit=1)[-1].title()} — leave request",
                         body=body, request=task.request)


def _escalate(task) -> None:
    """Notify the responsible higher authority, and log that it was done."""
    request = task.request
    recipients = {uid for uid in (task.assignee_user_id, request.unit_head_user_id)
                  if uid}
    for user_id in recipients:
        notifications.notify(
            topic="leave.escalated", dedupe_key=f"leave.escalated:{task.pk}:{user_id}",
            recipient_user_id=user_id,
            subject="A leave request has passed its escalation threshold",
            body=(f"{request.get_category_display()} {request.from_date} to "
                  f"{request.to_date} is still at the {task.stage} stage."),
            request=request)
