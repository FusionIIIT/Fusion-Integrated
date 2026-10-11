"""Which SLA threshold a task has reached (BR-EL-032, BR-EL-033, BR-EL-038).

The pending-only guard is the substance of both rules: a task that has been
decided is not reminded and not escalated, however far past its threshold the
clock has run. That guard is deliberately *not* here — it belongs to the
caller's query — but `decision` makes the two outcomes explicit rather than
leaving the caller to infer them from elapsed hours.

Pure Python: the clock arrives as an argument.
"""
from __future__ import annotations

from datetime import datetime, timedelta

REMIND = "remind"
ESCALATE = "escalate"
NONE = "none"


def is_due(*, assigned_at: datetime, now: datetime, threshold_hours: int) -> bool:
    return now - assigned_at >= timedelta(hours=threshold_hours)


def decision(*, assigned_at: datetime, now: datetime, reminder_hours: int,
             escalation_hours: int, reminded_at: datetime | None = None,
             escalated_at: datetime | None = None) -> str:
    """The strongest action this task has earned, at most one per threshold.

    Escalation wins over a reminder the sweep missed: a task past both
    thresholds must not be reminded politely and left there.
    """
    if escalated_at is None and is_due(assigned_at=assigned_at, now=now,
                                       threshold_hours=escalation_hours):
        return ESCALATE
    if reminded_at is None and is_due(assigned_at=assigned_at, now=now,
                                      threshold_hours=reminder_hours):
        return REMIND
    return NONE
