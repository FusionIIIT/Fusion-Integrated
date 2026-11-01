from datetime import timedelta
from django.utils import timezone
from modules.elm.models import LeavePolicy, LeaveRequest, SlaAction
from modules.elm.services.notifications import notify

PENDING = {"awaiting_substitute", "awaiting_unit_head", "awaiting_establishment", "awaiting_sanction", "awaiting_director", "cancellation_pending", "resumption_pending"}

def process(now=None) -> dict:
    now = now or timezone.now()
    policy = LeavePolicy.objects.filter(key="current").first()
    cfg = (policy.params or {}).get("sla", {}) if policy else {}
    reminder_hours = cfg.get("reminder_hours")
    escalation_hours = cfg.get("escalation_hours")
    escalation_role = cfg.get("escalation_role", "")
    if reminder_hours is None and escalation_hours is None:
        return {"processed": 0, "reminders": 0, "escalations": 0, "disabled": True}
    counts = {"processed": 0, "reminders": 0, "escalations": 0, "disabled": False}
    qs = LeaveRequest.objects.filter(status__in=PENDING).exclude(submitted_at__isnull=True)
    for req in qs.iterator():
        counts["processed"] += 1
        latest_stage = req.transitions.filter(to_status=req.status).order_by("-created_at").first()
        stage_started = latest_stage.created_at if latest_stage else req.submitted_at
        stage_key = latest_stage.pk if latest_stage else req.stage
        age = now - stage_started
        if reminder_hours is not None and age >= timedelta(hours=float(reminder_hours)):
            action, created = SlaAction.objects.get_or_create(request=req, stage=stage_key, action="reminder", defaults={"target_role": req.current_role})
            if created:
                notify(topic="sla_reminder", title="Leave request pending", body=f"Leave request #{req.pk} is still awaiting action.", role=req.current_role, payload={"request_id": req.pk})
                counts["reminders"] += 1
        if escalation_hours is not None and age >= timedelta(hours=float(escalation_hours)):
            action, created = SlaAction.objects.get_or_create(request=req, stage=stage_key, action="escalation", defaults={"target_role": escalation_role})
            if created:
                notify(topic="sla_escalation", title="Leave request escalated", body=f"Leave request #{req.pk} exceeded the escalation threshold.", role=escalation_role, payload={"request_id": req.pk})
                counts["escalations"] += 1
    return counts
