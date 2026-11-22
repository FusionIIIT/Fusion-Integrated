"""HR-EIS tasks have no assumed institutional scheduling cadence."""

from __future__ import annotations

import os
from datetime import timedelta

TASK_ROUTES = {
    "hreis.generate_notifications": {"queue": "notifications"},
    "hreis.deliver_notifications": {"queue": "notifications"},
}


def _configured_interval(name: str) -> timedelta | None:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return None
    try:
        minutes = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer number of minutes.") from exc
    if not 1 <= minutes <= 1440:
        raise ValueError(f"{name} must be between 1 and 1440 minutes.")
    return timedelta(minutes=minutes)


def configured_beat_schedule() -> dict:
    result = {}
    reminders = _configured_interval("HREIS_REMINDER_POLL_MINUTES")
    delivery = _configured_interval("HREIS_DELIVERY_POLL_MINUTES")
    if reminders is not None:
        result["hreis.generate-reminders"] = {
            "task": "hreis.generate_notifications",
            "schedule": reminders,
        }
    if delivery is not None:
        result["hreis.deliver-emails"] = {
            "task": "hreis.deliver_notifications",
            "schedule": delivery,
        }
    return result


BEAT_SCHEDULE = configured_beat_schedule()
