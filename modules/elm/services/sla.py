"""SLA reminder and escalation sweep (EL-UC-021).

Runs on the beat. For every **pending** task:

* at the reminder threshold — notify the assignee;
* at the escalation threshold — notify (or, when
  configured, reassign to) the configured authority.

Completed and cancelled tasks are never touched:
SLA clocks stop when the work stops (BR-EL-034).
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from modules.elm.models import LeaveTask, SlaEventLog
from modules.elm.services import notifications

log = logging.getLogger("fusion.elm.sla")


@transaction.atomic
def sweep(now=None) -> dict:
    """One SLA sweep. Returns what it did."""
    now = now or timezone.now()
    reminded = escalated = 0
    for task in LeaveTask.objects.filter(
            status="pending"):
        if (task.reminder_at is not None
                and now >= task.reminder_at
                and task.reminded_at is None):
            _remind(task, now)
            reminded += 1
        if (task.escalation_at is not None
                and now >= task.escalation_at
                and task.escalated_at is None):
            _escalate(task, now)
            escalated += 1
    return {"reminded": reminded,
            "escalated": escalated}


def _remind(task: LeaveTask, now) -> None:
    task.reminded_at = now
    task.save(update_fields=["reminded_at",
                                  "updated_at"])
    notifications.notify(
        task.assignee_user_id, "sla_reminder",
        f"Reminder: {task.task_class.replace('_', ' ')} "
        f"on leave request {task.request_id}",
        "This leave task has reached its reminder "
        "threshold and is still pending.",
        payload={"task_id": task.id,
                 "request_id": task.request_id,
                 "task_class": task.task_class},
        dedupe_key=(f"reminder:{task.id}:"
                    f"{task.reminded_at.isoformat()}"))
    SlaEventLog.objects.create(
        task=task, kind="reminder",
        detail={"assignee_user_id":
                task.assignee_user_id})
    _log_event(task, "reminder",
                 {"assignee_user_id":
                  task.assignee_user_id})


def _escalate(task: LeaveTask, now) -> None:
    config = None
    from modules.elm.models import SlaConfig

    config = SlaConfig.objects.filter(
        task_class=task.task_class).first()
    detail = {"assignee_user_id":
              task.assignee_user_id}

    if (config is not None
            and config.escalation_action == "reassign"
            and config.escalation_target_role):
        # XTP-EL-01: escalation changes routing or
        # responsibility only where configured.
        from modules.elm.models import EmployeeProfile

        targets = list(
            EmployeeProfile.objects.filter(
                designation_name=(
                    config.escalation_target_role),
                is_active=True).values_list(
                    "user_id", flat=True))
        if targets:
            previous = task.assignee_user_id
            task.assignee_user_id = sorted(targets)[0]
            detail["reassigned_from"] = previous
            detail["reassigned_to"] = (
                task.assignee_user_id)
            notifications.notify(
                previous, "sla_escalation",
                f"Escalated away: {task.task_class} "
                f"on request {task.request_id}",
                "This task passed its escalation "
                "threshold and was reassigned.",
                payload={"task_id": task.id,
                         "request_id": task.request_id},
                dedupe_key=(f"escalate-out:{task.id}:"
                            f"{now.isoformat()}"))

    task.escalated_at = now
    task.escalation_detail = detail
    task.save(update_fields=["escalated_at",
                                  "escalation_detail",
                                  "assignee_user_id",
                                  "updated_at"])

    if config is not None and config.escalation_target_role:
        from modules.elm.models import EmployeeProfile

        for holder in EmployeeProfile.objects.filter(
                designation_name=(
                    config.escalation_target_role),
                is_active=True).values_list(
                    "user_id", flat=True):
            notifications.notify(
                holder, "sla_escalation",
                f"Escalation: {task.task_class} on "
                f"request {task.request_id}",
                "A leave task passed its escalation "
                "threshold and is still pending.",
                payload={"task_id": task.id,
                         "request_id": task.request_id,
                         "task_class": task.task_class},
                dedupe_key=(
                    f"escalate:{task.id}:{holder}:"
                    f"{now.isoformat()}"))

    SlaEventLog.objects.create(
        task=task, kind="escalation", detail=detail)
    _log_event(task, "escalation", detail)


def _log_event(task: LeaveTask, kind: str,
                 payload: dict) -> None:
    from modules.elm.models import RequestEvent

    RequestEvent.objects.create(
        request=task.request,
        event=kind,
        outcome=task.task_class,
        payload={"task_id": task.id, **payload})
