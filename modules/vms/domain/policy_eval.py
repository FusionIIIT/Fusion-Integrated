"""Access-policy arithmetic (pure Python). BR-193, BR-202, BR-203, visiting hours (CFR-006)."""
from __future__ import annotations

from datetime import datetime, time, timedelta, tzinfo


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


def is_same_day(now: datetime, start: datetime, tz: tzinfo | None = None) -> bool:
    """True when both instants fall on one calendar day in ``tz`` (BR-203).

    Aware datetimes are converted to ``tz`` first: comparing ``.date()`` of a UTC value with
    a campus-zone value gives the wrong day for the first hours after local midnight.
    Naive datetimes are taken as already local.
    """
    def local(dt: datetime) -> datetime:
        return dt.astimezone(tz) if tz is not None and dt.tzinfo is not None else dt

    return local(now).date() == local(start).date()
