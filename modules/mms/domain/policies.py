"""Specification-backed validation for MMS dates and request decisions."""

from datetime import date, timedelta


class PolicyViolation(Exception):
    """A request conflicts with a frozen MMS business rule."""


def validate_rebate(
    *,
    start_date: date,
    end_date: date,
    submitted_on: date,
    reason: str,
    explanation: str,
    overlapping: bool,
) -> None:
    """Validate the explicit minimum, lead-time, reason, and overlap rules."""
    if end_date < start_date or (end_date - start_date).days + 1 < 3:
        raise PolicyViolation("A rebate must cover at least three calendar days.")
    if start_date < submitted_on + timedelta(days=1):
        raise PolicyViolation("A rebate must be requested at least one calendar day ahead.")
    if reason == "other" and not explanation.strip():
        raise PolicyViolation("An explanation is required for reason 'other'.")
    if overlapping:
        raise PolicyViolation("Rebate requests for the same student cannot overlap.")


def next_calendar_day(decided_on: date) -> date:
    """Return the service date for an approved deregistration."""
    return decided_on + timedelta(days=1)
