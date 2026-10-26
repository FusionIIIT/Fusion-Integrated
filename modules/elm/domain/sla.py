"""Reminder and escalation timing (BR-EL-032, BR-EL-033)."""
from __future__ import annotations

from datetime import datetime, timedelta

REMIND, ESCALATE = "remind", "escalate"


def due_action(*, waiting_since: datetime, now: datetime, remind_after: timedelta,
               escalate_after: timedelta, reminded: bool, escalated: bool) -> str | None:
    """The one thing to do now for a task still pending, or nothing."""
    waited = now - waiting_since
    if waited >= escalate_after and not escalated:
        return ESCALATE
    if waited >= remind_after and not reminded and not escalated:
        return REMIND
    return None
