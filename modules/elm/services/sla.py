"""Reminders and escalations for tasks left waiting (BR-EL-032/033, WF-EL-08)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

from modules.elm.domain import sla as rules
from modules.elm.domain import workflow as wf
from modules.elm.models import LeaveApplication, LeaveEvent
from modules.elm.services.common import PERMISSION_FOR_OWNER, notify


@dataclass
class SlaReport:
    reminded: int = 0
    escalated: int = 0


def remind_after() -> timedelta:
    return timedelta(hours=getattr(settings, "ELM_SLA_REMIND_HOURS", 48))


def escalate_after() -> timedelta:
    return timedelta(hours=getattr(settings, "ELM_SLA_ESCALATE_HOURS", 96))


def escalation_permission() -> str:
    return getattr(settings, "ELM_SLA_ESCALATION_PERMISSION", "elm.leave.administer")


def run(now: datetime | None = None) -> SlaReport:
    """Safe to run as often as you like: each step is recorded once."""
    now = now or timezone.now()
    report = SlaReport()
    waiting = LeaveApplication.objects.filter(status__in=list(wf.TASK_OWNER))
    for application in waiting.iterator():
        action = rules.due_action(
            waiting_since=application.waiting_since, now=now, remind_after=remind_after(),
            escalate_after=escalate_after(), reminded=application.reminded_at is not None,
            escalated=application.escalated_at is not None)
        if action is None:
            continue
        owner = wf.TASK_OWNER[application.status]
        label = f"{application.leave_type} {application.start_date}..{application.end_date}"
        if action == rules.REMIND:
            application.reminded_at = now
            application.save(update_fields=["reminded_at", "updated_at"])
            notify(application, "leave.reminder", f"Reminder: a leave awaits you ({label}).",
                   user_id=application.substitute_user_id
                   if owner == wf.SUBSTITUTE else None,
                   permission=PERMISSION_FOR_OWNER.get(owner, ""),
                   key=f"sla-remind-{application.status}-{application.waiting_since:%s}")
            report.reminded += 1
        else:
            application.escalated_at = now
            application.save(update_fields=["escalated_at", "updated_at"])
            LeaveEvent.objects.create(
                application=application, action="sla_escalated",
                from_status=application.status, to_status=application.status,
                note=f"Pending since {application.waiting_since:%Y-%m-%d %H:%M}")
            notify(application, "leave.escalation", f"Escalation: a leave is overdue ({label}).",
                   permission=escalation_permission(),
                   key=f"sla-escalate-{application.status}-{application.waiting_since:%s}")
            report.escalated += 1
    return report
