"""Access-policy arithmetic (pure Python). BR-193, BR-202, BR-203, visiting hours (CFR-006)."""
from __future__ import annotations

from datetime import datetime, time, timedelta


def within_visiting_hours(at: datetime | time, start: time, end: time) -> bool:
    """Inclusive window. A window with start > end wraps midnight."""
    t = at.time() if isinstance(at, datetime) else at
    if start <= end:
        return start <= t <= end
    return t >= start or t <= end


def capped_end(start: datetime, end: datetime, max_hours: float) -> datetime:
    """``end`` limited to ``start + max_hours`` (BR-193). Never earlier than ``start``."""
    limit = start + timedelta(hours=max_hours)
    return max(start, min(end, limit))


def advance_ok(now: datetime, start: datetime, hours: float) -> bool:
    """True when the visit starts at least ``hours`` after ``now`` (BR-202)."""
    return start - now >= timedelta(hours=hours)


def is_same_day(now: datetime, start: datetime) -> bool:
    return now.date() == start.date()
