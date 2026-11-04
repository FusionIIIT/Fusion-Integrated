"""SLA monitoring, reminder dispatch, and renewal reminders for SPACS.

Enforces:
- CFR-SPACS-007 / AFR-SPACS-026 (Review SLA Reminder and Escalation)
- CFR-SPACS-012 / AFR-SPACS-041 (Renewal Reminders)
- BR-SPACS-013 (Review SLA and Escalation)
- UC-SPACS-024 (Issue SLA Reminder / Escalation)
- UC-SPACS-025 (Send Scholarship Renewal Reminder)
- Stage-aware notification tracking with deduplication keys
- Notification delivery failures never mutate application or task business state
"""
from __future__ import annotations

import logging
from django.db import transaction
from django.utils import timezone as dj_timezone

from modules.spacs.domain.sla import evaluate_due_sla_stages
from modules.spacs.models import SpacsTask, ScholarshipApplication
from modules.spacs.services.notifications import enqueue as enqueue_notification

log = logging.getLogger("fusion.spacs.sla")


def process_pending_tasks_sla() -> int:
    """Evaluates SLA stages for all pending tasks and enqueues due reminders (UC-SPACS-024).

    Guarantees that each configured stage is enqueued only once per task.
    Notification failure never mutates business state.
    """
    now = dj_timezone.now()
    pending_tasks = SpacsTask.objects.filter(status="pending").select_related("application", "award_cycle")
    dispatched_count = 0

    for task in pending_tasks:
        if not task.sla_snapshot:
            continue

        notified_keys = {
            item["stage"] for item in (task.sla_notified_stages or []) if isinstance(item, dict) and "stage" in item
        }

        due_stages = evaluate_due_sla_stages(
            sla_snapshot=task.sla_snapshot,
            task_created_at=task.created_at,
            already_notified_stage_keys=notified_keys,
            now=now,
        )

        if not due_stages:
            continue

        for stage in due_stages:
            stage_key = stage["key"]
            recipient_role = stage.get("recipient_role", task.assigned_role)
            is_escalation = stage.get("is_escalation", False)
            topic = "sla.escalation" if is_escalation else "sla.reminder"
            dedupe_key = f"spacs.sla.{task.id}.{stage_key}"

            target_desc = f"Application #{task.application_id}" if task.application_id else f"Award Cycle #{task.award_cycle_id}"
            subject = f"[{'ESCALATION' if is_escalation else 'REMINDER'}] SPACS Task Pending: {task.task_type}"
            body = (
                f"The task '{task.task_type}' for {target_desc} is pending review. "
                f"Configured threshold for stage '{stage_key}' has been reached."
            )

            # Enqueue outbox notification
            enqueue_notification(
                topic=topic,
                dedupe_key=dedupe_key,
                subject=subject,
                body=body,
                recipient_user_id=task.assigned_user_id,
                payload={
                    "task_id": task.id,
                    "stage": stage_key,
                    "role": recipient_role,
                },
            )

            # Record stage in task's stage tracking list
            with transaction.atomic():
                current_stages = list(task.sla_notified_stages or [])
                current_stages.append({
                    "stage": stage_key,
                    "sent_at": now.isoformat(),
                    "recipient_role": recipient_role,
                })
                task.sla_notified_stages = current_stages
                task.save(update_fields=["sla_notified_stages", "updated_at"])

            dispatched_count += 1
            log.info("spacs.sla.dispatched task=%s stage=%s", task.id, stage_key)

    return dispatched_count


def process_scholarship_renewal_reminders() -> int:
    """Enqueues renewal reminders for eligible past awardees before deadline (UC-SPACS-025, AFR-SPACS-041)."""
    now = dj_timezone.now()
    # Find active renewal-eligible applications
    eligible_apps = (
        ScholarshipApplication.objects.filter(
            status="approved",
            policy_version__is_renewable=True,
            policy_version__renewal_window_end__gte=now,
            policy_version__renewal_window_start__lte=now,
        )
        .select_related("policy_version", "policy_version__catalogue_entry")
    )

    reminders_sent = 0
    for app in eligible_apps:
        cycle = app.academic_cycle
        policy = app.policy_version
        dedupe_key = f"spacs.renewal.remind.{app.id}.{cycle}"

        res = enqueue_notification(
            topic="renewal.reminder",
            dedupe_key=dedupe_key,
            subject=f"Renewal Window Open: {policy.catalogue_entry.title}",
            body=f"The renewal window for {policy.catalogue_entry.title} is now open for cycle {cycle}. Please submit your updated evidence.",
            recipient_user_id=app.user_id,
            payload={"prior_application_id": app.id},
        )
        if res:
            reminders_sent += 1

    return reminders_sent
