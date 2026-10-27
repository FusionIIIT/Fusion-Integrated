"""Pending-only SLA reminder and escalation processing."""
from datetime import timedelta
from django.utils import timezone
from modules.leave.models import LeaveActionHistory, LeaveApplication, LeavePolicyConfig
from modules.leave.services.notifications import enqueue as enqueue_notification


def _setting(key: str, default: int) -> int:
    row = LeavePolicyConfig.objects.filter(key=key).first()
    try:
        return max(1, int(row.value)) if row else default
    except (TypeError, ValueError):
        return default


def _task_assignment(app: LeaveApplication):
    if app.status == "substitute_pending":
        req = app.substitute_requests.filter(status="pending", is_current=True).first()
        return (req.substitute_user_id, req.created_at, "substitute") if req else (None, None, "substitute")
    if app.status == "resumption_submitted":
        return app.sanctioning_authority_user_id or app.establishment_user_id, app.updated_at, "resumption"
    if app.status in {"cancel_requested", "under_review", "extension_requested"}:
        if app.unit_head_user_id and app.unit_head_reviewed_at is None:
            return app.unit_head_user_id, app.updated_at, "unit_head"
        if app.establishment_user_id and app.establishment_reviewed_at is None:
            return app.establishment_user_id, app.updated_at, "establishment"
        return app.sanctioning_authority_user_id, app.updated_at, "sanction"
    return None, None, ""


def process_sla_thresholds(*, now=None) -> dict[str, int]:
    now = now or timezone.now()
    reminder_after = timedelta(hours=_setting("sla.reminder_hours", 24))
    escalation_after = timedelta(hours=_setting("sla.escalation_hours", 72))
    escalation_cfg = LeavePolicyConfig.objects.filter(key="sla.escalation_user_id").first()
    escalation_user_id = None
    if escalation_cfg:
        try:
            escalation_user_id = int(escalation_cfg.value)
        except (TypeError, ValueError):
            escalation_user_id = None

    result = {"reminders": 0, "escalations": 0, "skipped": 0}
    active = LeaveApplication.objects.filter(
        status__in=["substitute_pending", "under_review", "extension_requested", "cancel_requested", "resumption_submitted"]
    ).order_by("updated_at")
    for app in active.iterator():
        recipient, assigned_at, task_class = _task_assignment(app)
        if not recipient or not assigned_at:
            result["skipped"] += 1
            continue
        age = now - assigned_at
        task_key = f"{app.status}:{task_class}:{assigned_at.isoformat()}"
        if age >= reminder_after and not LeaveActionHistory.objects.filter(
            application=app, action="sla_reminder", remarks__contains=task_key
        ).exists():
            if not LeaveApplication.objects.filter(pk=app.pk, status=app.status).exists():
                continue
            LeaveActionHistory.objects.create(
                application=app, actor_user_id=0, actor_role="system", action="sla_reminder",
                remarks=task_key,
            )
            enqueue_notification(
                recipient_user_id=recipient, topic="workflow.reminder",
                dedupe_key=f"leave:{app.pk}:reminder:{task_key}",
                subject="Leave workflow task reminder",
                body=f"Leave request #{app.pk} remains assigned to you for {task_class} review.",
            )
            result["reminders"] += 1
        if age >= escalation_after and not LeaveActionHistory.objects.filter(
            application=app, action="sla_escalation", remarks__contains=task_key
        ).exists():
            if not LeaveApplication.objects.filter(pk=app.pk, status=app.status).exists():
                continue
            target = escalation_user_id or app.establishment_user_id or app.sanctioning_authority_user_id
            if not target or target == recipient:
                result["skipped"] += 1
                continue
            LeaveActionHistory.objects.create(
                application=app, actor_user_id=0, actor_role="system", action="sla_escalation",
                remarks=task_key,
            )
            enqueue_notification(
                recipient_user_id=target, topic="workflow.escalation",
                dedupe_key=f"leave:{app.pk}:escalation:{task_key}",
                subject="Leave workflow task escalation",
                body=f"Leave request #{app.pk} remains pending with {task_class} beyond the configured escalation threshold.",
            )
            result["escalations"] += 1
    return result
