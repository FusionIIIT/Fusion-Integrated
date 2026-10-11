"""SLA threshold processing (EL-UC-021, BR-EL-032/033/038).

EVT-02 is a trigger, not an actor. The pending-only guard is the substance of
both rules: a task that has since been decided is not reminded and not
escalated, and the sweep asks the *task* whether it is still pending rather
than trusting the query that found it.

An escalation configured as `notify` writes a notification only. One configured
as `reassign` changes routing/responsibility, which is XTP-EL-01 — the only
place in this module a background job moves a task between offices.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from modules.leave.domain import sla as rules
from modules.leave.models import SlaEvent, WorkflowTask
from modules.leave.selectors import leave as sel
from modules.leave.services import notifications

log = logging.getLogger("fusion.leave.sla")


@transaction.atomic
def process(*, now=None, limit: int = 500) -> dict[str, int]:
    """One sweep: remind or escalate every pending task that has earned it."""
    now = now or timezone.now()
    thresholds = sel.sla_thresholds()
    report = {"reminded": 0, "escalated": 0, "skipped": 0}
    if not thresholds:
        return report

    widest = max(t.escalation_hours for t in thresholds.values())
    horizon = now - timedelta(hours=widest)
    candidates = (WorkflowTask.objects
                  .filter(status="pending", task_class__in=list(thresholds),
                          assigned_at__lte=now)
                  .order_by("assigned_at")[:limit])

    for task in candidates:
        threshold = thresholds.get(task.task_class)
        if threshold is None:
            continue
        # Re-read under the row lock: the pending-only guard must judge the task
        # as it is now, not as the sweep's query saw it.
        locked = WorkflowTask.objects.select_for_update().filter(pk=task.pk).first()
        if locked is None or locked.status != "pending":
            report["skipped"] += 1
            continue
        if locked.assigned_at > horizon and locked.reminded_at is not None:
            continue

        action = rules.decision(
            assigned_at=locked.assigned_at, now=now,
            reminder_hours=threshold.reminder_hours,
            escalation_hours=threshold.escalation_hours,
            reminded_at=locked.reminded_at, escalated_at=locked.escalated_at)

        if action == rules.REMIND:
            _remind(task=locked, threshold=threshold, now=now)
            report["reminded"] += 1
        elif action == rules.ESCALATE:
            _escalate(task=locked, threshold=threshold, now=now)
            report["escalated"] += 1

    if any(report.values()):
        log.info("leave.sla.run %s", report)
    return report


def _remind(*, task: WorkflowTask, threshold, now) -> None:
    task.reminded_at = now
    task.save(update_fields=["reminded_at", "updated_at"])
    SlaEvent.objects.create(task=task, kind="reminder",
                            threshold_hours=threshold.reminder_hours,
                            recipient_user_id=task.assignee_user_id,
                            note=f"{threshold.task_class} awaiting a decision")
    notifications.enqueue(
        topic="leave.sla.reminder",
        dedupe_key=f"leave.sla:{task.pk}:reminder:{threshold.reminder_hours}",
        recipient_user_id=task.assignee_user_id,
        subject="A leave task is still awaiting your decision",
        body=(f"{threshold.task_class.replace('.', ' ')} has been pending for "
              f"{threshold.reminder_hours}+ hours."),
        payload={"task_id": task.pk, "request_id": task.request_id})


def _escalate(*, task: WorkflowTask, threshold, now) -> None:
    """BR-EL-033 — the configured escalation action, and only if still pending."""
    task.escalated_at = now
    fields = ["escalated_at", "updated_at"]
    if threshold.escalation_action == "reassign" and threshold.escalate_to_role:
        # XTP-EL-01: routing/responsibility changes, so the task moves.
        task.assignee_role = threshold.escalate_to_role
        task.assignee_user_id = None
        fields += ["assignee_role", "assignee_user_id"]
    task.save(update_fields=fields)

    how = (f"routing changed to {threshold.escalate_to_role}"
           if threshold.escalation_action == "reassign" else "notification only")
    SlaEvent.objects.create(
        task=task, kind="escalation",
        threshold_hours=threshold.escalation_hours,
        recipient_user_id=task.assignee_user_id,
        note=f"{threshold.task_class} escalated ({how})"[:300])
    notifications.enqueue(
        topic="leave.sla.escalation",
        dedupe_key=f"leave.sla:{task.pk}:escalation:{threshold.escalation_hours}",
        recipient_user_id=task.assignee_user_id,
        subject="A leave task has breached its SLA",
        body=(f"{threshold.task_class.replace('.', ' ')} passed "
              f"{threshold.escalation_hours} hours; escalated to "
              f"{threshold.escalate_to_role or 'the configured authority'}."),
        payload={"task_id": task.pk, "request_id": task.request_id,
                 "escalation_action": threshold.escalation_action})
