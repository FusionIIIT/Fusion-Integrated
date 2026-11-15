"""Scheduled SLA reminders and escalations (SF-EL-002, WF-EL-08)."""
from __future__ import annotations

from datetime import datetime, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from modules.elm.domain import state_machine as sm
from modules.elm.models import LeaveRequest, SlaAction
from modules.elm.selectors import config as config_sel
from modules.elm.services import notify

ACTIONABLE = (sm.PENDING - {sm.SUBSTITUTE_DECLINED}) | {
    sm.CANCELLATION_PENDING, sm.RESUMPTION_PENDING}


def _log(req: LeaveRequest, action: str, target: str) -> bool:
    try:
        with transaction.atomic():
            SlaAction.objects.create(request=req, status=req.status, stage=req.stage,
                                     stage_entered_at=req.stage_entered_at,
                                     action=action, target_role=target)
    except IntegrityError:
        return False
    return True


def process(now: datetime | None = None) -> dict:
    now = now or timezone.now()
    pv = config_sel.effective_policy()
    sla = ((pv.hierarchy if pv else {}) or {}).get("sla") or {}
    remind_h, escalate_h = sla.get("reminder_hours"), sla.get("escalation_hours")
    escalate_to = sla.get("escalate_to") or ""
    report = {"reminders": 0, "escalations": 0}
    if not remind_h and not escalate_h:
        return report
    for req in LeaveRequest.objects.filter(status__in=ACTIONABLE,
                                           stage_entered_at__isnull=False):
        age = now - req.stage_entered_at
        target = req.current_role or f"user:{req.substitute_user_id}"
        if (remind_h and age >= timedelta(hours=float(remind_h))
                and _log(req, SlaAction.REMINDER, target)):
            report["reminders"] += 1
            msg = f"Reminder: leave #{req.pk} is still awaiting your action."
            if req.status == sm.AWAITING_SUBSTITUTE:
                notify.to_user(req.substitute_user_id, req, msg)
            else:
                notify.to_role(req.current_role, req, msg)
        if (escalate_h and escalate_to and age >= timedelta(hours=float(escalate_h))
                and _log(req, SlaAction.ESCALATION, escalate_to)):
            report["escalations"] += 1
            notify.to_role(escalate_to, req,
                           f"Escalation: leave #{req.pk} has waited at "
                           f"{req.status.replace('_', ' ')} beyond its SLA.")
    return report
