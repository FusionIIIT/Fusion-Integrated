"""Event-triggered SLA threshold processing (EL-UC-021, BR-EL-031, BR-EL-032)."""

from django.utils import timezone

from modules.leave.models import LeaveActionLog, LeaveApplication, LeaveSLAConfig


def process_sla_thresholds() -> dict:
    """Check pending actionable workflow tasks against SLA thresholds."""
    now = timezone.now()
    configs = {c.task_type: c for c in LeaveSLAConfig.objects.all()}
    default_reminder_hours = 48
    default_escalation_hours = 96

    pending_apps = LeaveApplication.objects.filter(
        status__in=[
            "AWAITING_SUBSTITUTE",
            "AWAITING_UNIT_HEAD",
            "AWAITING_ESTABLISHMENT",
            "AWAITING_SANCTION",
        ]
    )

    reminded = 0
    escalated = 0

    for app in pending_apps:
        age_hours = (now - app.created_at).total_seconds() / 3600
        cfg = configs.get(app.status)
        rem_threshold = cfg.reminder_threshold_hours if cfg else default_reminder_hours
        esc_threshold = cfg.escalation_threshold_hours if cfg else default_escalation_hours

        if age_hours >= esc_threshold:
            escalated += 1
            LeaveActionLog.objects.create(
                application=app,
                actor_user_id=0,
                action="SLA_ESCALATE",
                from_status=app.status,
                to_status=app.status,
                remarks=f"SLA Escalation: pending {int(age_hours)}h (limit {esc_threshold}h)",
            )
        elif age_hours >= rem_threshold:
            reminded += 1
            LeaveActionLog.objects.create(
                application=app,
                actor_user_id=0,
                action="SLA_REMIND",
                from_status=app.status,
                to_status=app.status,
                remarks=f"SLA Reminder: pending {int(age_hours)}h (limit {rem_threshold}h)",
            )

    return {"reminded": reminded, "escalated": escalated}
