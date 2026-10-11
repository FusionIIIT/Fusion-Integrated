from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from modules.leave.domain.workflow import PENDING_STATES
from modules.leave.models import LeaveApplication, LeaveNotification, SlaConfiguration


def process_thresholds(now=None) -> dict[str, int]:
    now = now or timezone.now()
    result = {"reminders": 0, "escalations": 0}
    for application in LeaveApplication.objects.filter(status__in=PENDING_STATES):
        assigned_at = application.task_assigned_at or application.submitted_at
        if assigned_at is None:
            continue
        config = SlaConfiguration.objects.filter(task_kind=application.status).first()
        if config is None:
            continue
        elapsed = now - assigned_at
        if config.reminder_after_hours is not None and elapsed >= timedelta(
                hours=config.reminder_after_hours):
            row, created = LeaveNotification.objects.get_or_create(
                dedupe_key=f"sla-reminder:{application.pk}:{application.status}:{assigned_at.isoformat()}",
                defaults={
                    "topic": "sla_reminder",
                    "recipient_user_id": _assignee(application),
                    "subject": "Leave task reminder",
                    "body": f"Leave request {application.pk} is still awaiting action.",
                },
            )
            if created:
                result["reminders"] += 1
        if (config.escalation_after_hours is not None
                and elapsed >= timedelta(hours=config.escalation_after_hours)):
            assignee = _assignee(application)
            target = config.escalation_user_id or assignee
            key = f"sla-escalation:{application.pk}:{application.status}:{assigned_at.isoformat()}"
            with transaction.atomic():
                _, created = LeaveNotification.objects.get_or_create(
                    dedupe_key=key,
                    defaults={
                        "topic": "sla_escalation", "recipient_user_id": target,
                        "subject": "Leave task escalation",
                        "body": f"Leave request {application.pk} passed its configured SLA threshold.",
                    },
                )
                if created and config.escalation_user_id:
                    field = _assignee_field(application)
                    setattr(application, field, config.escalation_user_id)
                    application.task_assigned_at = now
                    application.save(update_fields=[field, "task_assigned_at", "updated_at"])
                    result["escalations"] += 1
    return result


def _assignee(application: LeaveApplication) -> int:
    value = getattr(application, _assignee_field(application))
    return value or application.applicant_user_id


def _assignee_field(application: LeaveApplication) -> str:
    state = application.status
    if "substitute_response" in state:
        return "substitute_user_id"
    if "unit_head_review" in state:
        return "unit_head_user_id"
    if "establishment" in state:
        return "establishment_user_id"
    return "final_authority_user_id"
