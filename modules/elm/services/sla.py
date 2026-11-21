"""Event-triggered SLA threshold processing services (EL-UC-021 / CFR-EL-031 / CFR-EL-032)."""
from __future__ import annotations

from datetime import datetime

from django.db import transaction
from django.utils import timezone

from modules.elm.domain.sla import evaluate_task_sla
from modules.elm.models import LeaveAuditLog, WorkflowTask
from modules.elm.selectors.config import get_sla_config_for_task


@transaction.atomic
def process_sla_events(
    now: datetime | None = None,
) -> dict[str, int]:
    """Process SLA reminder and escalation thresholds for pending tasks (EL-UC-021).

    Enforces:
    - BR-EL-032: SLA reminder on still-pending task
    - BR-EL-033: SLA escalation on still-pending task
    - If task is no longer pending, no reminder or escalation is issued.
    """
    current_time = now or timezone.now()
    pending_tasks = WorkflowTask.objects.filter(status="pending")

    reminders_sent = 0
    escalations_processed = 0

    for task in pending_tasks:
        cfg = get_sla_config_for_task(task.task_type)
        remind_hrs = cfg.reminder_threshold_hours if cfg else 24
        esc_hrs = cfg.escalation_threshold_hours if cfg else 48

        eval_res = evaluate_task_sla(
            task_created_at=task.created_at,
            current_time=current_time,
            status=task.status,
            reminder_threshold_hours=remind_hrs,
            escalation_threshold_hours=esc_hrs,
            reminder_count=task.reminder_count,
            is_already_escalated=bool(task.escalated_at),
        )

        if eval_res.should_remind:
            task.reminder_sent_at = current_time
            task.reminder_count += 1
            task.save(update_fields=["reminder_sent_at", "reminder_count", "updated_at"])
            reminders_sent += 1

            if task.leave_application:
                LeaveAuditLog.objects.create(
                    leave_application=task.leave_application,
                    actor_user_id=None,
                    action="sla_reminder",
                    from_state=task.leave_application.status,
                    to_state=task.leave_application.status,
                    remarks=(
                        f"SLA reminder issued for task #{task.id} ({task.task_type}) "
                        f"to user #{task.assigned_to_user_id}"
                    ),
                    payload={"task_id": task.id, "reminder_count": task.reminder_count},
                )

        if eval_res.should_escalate:
            task.escalated_at = current_time
            escalations_processed += 1

            # If escalation changes routing/responsibility (XTP-EL-01 / BR-EL-033)
            if cfg and cfg.escalation_action == "escalate_routing" and cfg.escalation_target_role:
                # Log escalation routing
                pass

            task.save(update_fields=["escalated_at", "updated_at"])

            if task.leave_application:
                LeaveAuditLog.objects.create(
                    leave_application=task.leave_application,
                    actor_user_id=None,
                    action="sla_escalation",
                    from_state=task.leave_application.status,
                    to_state=task.leave_application.status,
                    remarks=f"SLA escalation executed for task #{task.id} ({task.task_type})",
                    payload={
                        "task_id": task.id,
                        "action": cfg.escalation_action if cfg else "notify_only",
                    },
                )

    return {
        "reminders_sent": reminders_sent,
        "escalations_processed": escalations_processed,
    }
