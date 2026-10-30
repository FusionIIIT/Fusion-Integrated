"""Configurable SLA threshold evaluation (Section 14)."""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SlaStatus:
    is_pending: bool
    should_remind: bool
    should_escalate: bool
    pending_hours: float


def evaluate_sla(
    is_pending: bool,
    created_at: datetime,
    now: datetime,
    reminder_hours: float = 48.0,
    escalation_hours: float = 96.0,
    already_reminded: bool = False,
    already_escalated: bool = False,
) -> SlaStatus:
    """Evaluate SLA reminder and escalation for actionable tasks (Section 14).

    - If task is still pending at reminder threshold, remind and log.
    - If task remains pending past escalation threshold, escalate and log.
    - No reminder or escalation is issued if the task is no longer pending.
    """
    if not is_pending:
        return SlaStatus(
            is_pending=False,
            should_remind=False,
            should_escalate=False,
            pending_hours=0.0,
        )

    elapsed_hours = (now - created_at).total_seconds() / 3600.0
    remind = (elapsed_hours >= reminder_hours) and not already_reminded
    escalate = (elapsed_hours >= escalation_hours) and not already_escalated

    return SlaStatus(
        is_pending=True,
        should_remind=remind,
        should_escalate=escalate,
        pending_hours=elapsed_hours,
    )
