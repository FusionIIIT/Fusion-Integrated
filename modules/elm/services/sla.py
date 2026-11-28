"""SLA reminder and escalation service (SF-EL-002, BR-EL-032, BR-EL-033)."""
from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from modules.elm.domain import state_machine as sm
from modules.elm.models import LeaveRequest, Notification, SlaAction
from modules.elm.selectors.config import effective_policy_version


@transaction.atomic
def process() -> dict:
    pv = effective_policy_version()
    sla_cfg = (pv.hierarchy.get("sla") if pv and isinstance(pv.hierarchy, dict) else None) or {}
    remind_hours = sla_cfg.get("reminder_hours")
    escalate_hours = sla_cfg.get("escalation_hours")
    escalation_role = sla_cfg.get("escalation_role")
    if not remind_hours and not escalate_hours:
        return {"reminders": 0, "escalations": 0}

    now = timezone.now()
    reminders = 0
    escalations = 0
    pending = LeaveRequest.objects.filter(
        status__in=list(sm.PENDING),
        stage_entered_at__isnull=False,
    )
    for req in pending:
        entered = req.stage_entered_at
        if entered is None or not req.current_role:
            continue
        if remind_hours and now - entered >= timedelta(hours=int(remind_hours)):
            _, created = SlaAction.objects.get_or_create(
                request=req,
                status=req.status,
                stage=req.stage,
                stage_entered_at=entered,
                action=SlaAction.REMINDER,
                defaults={"target_role": req.current_role},
            )
            if created:
                Notification.objects.create(
                    recipient_role=req.current_role,
                    request=req,
                    message=f"SLA reminder: Leave #{req.pk} awaits your action.",
                )
                reminders += 1
        if (escalate_hours and escalation_role
                and now - entered >= timedelta(hours=int(escalate_hours))):
            _, created = SlaAction.objects.get_or_create(
                request=req,
                status=req.status,
                stage=req.stage,
                stage_entered_at=entered,
                action=SlaAction.ESCALATION,
                defaults={"target_role": escalation_role},
            )
            if created:
                Notification.objects.create(
                    recipient_role=escalation_role,
                    request=req,
                    message=f"SLA escalation: Leave #{req.pk} overdue at {req.current_role}.",
                )
                escalations += 1
    return {"reminders": reminders, "escalations": escalations}
