"""SLA evaluation logic for actionable workflow tasks.

Pure Python — no Django imports allowed in domain/.
Enforces:
- BR-EL-032: SLA reminder on still-pending task
- BR-EL-033: SLA escalation on still-pending task
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TaskSlaEvaluation:
    should_remind: bool
    should_escalate: bool
    is_pending: bool


def evaluate_task_sla(
    task_created_at: datetime,
    current_time: datetime,
    status: str,
    reminder_threshold_hours: int,
    escalation_threshold_hours: int,
    reminder_count: int,
    is_already_escalated: bool,
) -> TaskSlaEvaluation:
    """Evaluate whether an actionable workflow task is eligible for SLA reminder or escalation.

    BR-EL-032 / BR-EL-033: Only still-pending tasks may be reminded or escalated.
    """
    if status != "pending":
        # Non-pending tasks suppress all reminders and escalations
        return TaskSlaEvaluation(
            should_remind=False,
            should_escalate=False,
            is_pending=False,
        )

    elapsed = current_time - task_created_at
    hours_elapsed = elapsed.total_seconds() / 3600.0

    # Remind if past reminder threshold and not yet reminded (or threshold reached)
    should_remind = (
        hours_elapsed >= reminder_threshold_hours
        and reminder_count == 0
        and not is_already_escalated
    )

    # Escalate if past escalation threshold and not yet escalated
    should_escalate = (
        hours_elapsed >= escalation_threshold_hours
        and not is_already_escalated
    )

    return TaskSlaEvaluation(
        should_remind=should_remind,
        should_escalate=should_escalate,
        is_pending=True,
    )
