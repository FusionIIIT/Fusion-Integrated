"""SLA reminders and escalations (BR-EL-032…034, EL-UC-021).

Swept on a timer by the module's beat schedule. Only files with an open task
qualify — terminal ones have their task closed, which is what keeps the SLA
per-step rather than forever-since-submission.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from modules.leave.models import LeaveRequest, LeaveRequestEvent, SlaThreshold
from modules.leave.services import notifications, workflow


def sweep(now=None) -> dict:
    now = now or timezone.now()
    reminded = escalated = 0

    with transaction.atomic():
        rows = list(LeaveRequest.objects
                    .select_for_update()
                    .exclude(task_class="")
                    .exclude(task_assigned_at=None))
        for request in rows:
            threshold = (SlaThreshold.objects
                         .filter(task_class=request.task_class).first())
            if threshold is None:
                continue
            holder = request.task_user_id
            reminder_target = holder or threshold.escalation_user_id
            escalation_target = threshold.escalation_user_id or holder
            if reminder_target is None and escalation_target is None:
                continue  # configured neither way: nothing to remind about

            age_hours = ((now - request.task_assigned_at).total_seconds()
                         / 3600)
            saved: list[str] = []

            if (threshold.reminder_hours and request.reminder_sent_at is None
                    and age_hours >= threshold.reminder_hours):
                notifications.notify(
                    reminder_target, "sla_reminder",
                    f"Reminder: {request.category.upper()} leave "
                    f"({request.start_date.isoformat()}…) assigned to you has "
                    f"been waiting {int(age_hours)} hours.", request)
                workflow.record_event(
                    request, LeaveRequestEvent.SLA_REMINDER,
                    note=f"after {threshold.reminder_hours}h → "
                         f"{reminder_target}")
                request.reminder_sent_at = now
                saved.append("reminder_sent_at")
                reminded += 1

            if (threshold.escalation_hours
                    and request.escalated_at is None
                    and age_hours >= threshold.escalation_hours):
                notifications.notify(
                    escalation_target, "sla_escalation",
                    f"Escalated: {request.category.upper()} leave "
                    f"({request.start_date.isoformat()}…) has been waiting "
                    f"{int(age_hours)} hours.", request)
                if threshold.escalation_user_id is not None:
                    # BR-EL-033: escalation can change routing, not merely
                    # notify — the new holder's clock starts now.
                    request.task_user_id = threshold.escalation_user_id
                    request.task_assigned_at = now
                    request.reminder_sent_at = None
                    saved += ["task_user_id", "task_assigned_at",
                              "reminder_sent_at"]
                request.escalated_at = now
                saved.append("escalated_at")
                workflow.record_event(
                    request, LeaveRequestEvent.SLA_ESCALATION,
                    note=f"after {threshold.escalation_hours}h → "
                         f"{escalation_target}")
                escalated += 1

            if saved:
                request.save(update_fields=[*saved, "updated_at"])

    return {"reminded": reminded, "escalated": escalated}
