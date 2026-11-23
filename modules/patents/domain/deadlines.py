from __future__ import annotations

from datetime import date, datetime, timedelta

DEFAULT_REVIEW_DAYS = 15
DEFAULT_REVISION_DAYS = 60

ALERT_INTERVAL_DAYS = (30, 15, 5)


def is_revision_expired(
    decision_date: datetime,
    now: datetime,
    limit_days: int = DEFAULT_REVISION_DAYS,
) -> bool:
    return now >= (decision_date + timedelta(days=limit_days))


def is_review_overdue(
    assigned_date: datetime,
    now: datetime,
    limit_days: int = DEFAULT_REVIEW_DAYS,
) -> bool:
    return now >= (assigned_date + timedelta(days=limit_days))


def calculate_days_remaining(deadline: date, current_date: date) -> int:
    return (deadline - current_date).days


def match_alert_interval(deadline: date, current_date: date) -> int | None:
    days = calculate_days_remaining(deadline, current_date)
    return days if days in ALERT_INTERVAL_DAYS else None
