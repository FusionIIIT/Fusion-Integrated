"""SLA threshold arithmetic for actionable tasks (BR-EL-032, BR-EL-033, BR-EL-038).

Both thresholds are guarded on the task still being pending, and both are
one-shot: a reminder that has already been logged is not logged again, because
an officer's queue is not a place to send the same line every hour.
"""
from __future__ import annotations

from dataclasses import dataclass

from modules.leave.domain.errors import RuleViolation

REMIND = "remind"
ESCALATE = "escalate"


@dataclass(frozen=True)
class Thresholds:
    reminder_hours: int
    escalation_hours: int


def validate(thresholds: Thresholds) -> Thresholds:
    """BR-EL-038: a threshold nobody can act on is not a configuration."""
    if thresholds.reminder_hours <= 0:
        raise RuleViolation("The reminder threshold must be a positive number of hours.",
                            code="threshold_invalid")
    if thresholds.escalation_hours < thresholds.reminder_hours:
        raise RuleViolation(
            "The escalation threshold cannot fall before the reminder threshold.",
            code="threshold_invalid")
    return thresholds


def events(*, thresholds: Thresholds, age_hours: float, pending: bool,
           reminded: bool = False, escalated: bool = False) -> tuple[str, ...]:
    """Which actions this pass of the sweep may take, in order."""
    if not pending:
        return ()

    due: list[str] = []
    if not reminded and age_hours >= thresholds.reminder_hours:
        due.append(REMIND)
    if not escalated and age_hours >= thresholds.escalation_hours:
        due.append(ESCALATE)
    return tuple(due)
