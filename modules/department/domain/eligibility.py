"""Pure-Python eligibility and validation logic for Department module.

Rules implemented:
- OA-BR-61: PG Scope Check. Only postgraduate students (e.g. M.Tech, Ph.D.,
  M.Des, or programme_level='PG') may initiate graduate seminar scheduling requests.
- Input validation: title/topic must be non-empty, preferred dates must not be in the past.
"""
from __future__ import annotations

import datetime
from typing import NamedTuple

PG_PROGRAMMES = frozenset({"M.Tech", "M.Des", "Ph.D.", "PhD", "MTech", "MDes", "PG"})


class EligibilityResult(NamedTuple):
    allowed: bool
    reason: str


def is_pg_student(programme: str | None) -> bool:
    """Check if the given programme indicates a postgraduate student (OA-BR-61)."""
    if not programme:
        return False
    clean = programme.strip()
    if clean.upper() in {"PG", "POSTGRADUATE"}:
        return True
    return any(clean.upper() == pg.upper() or pg.upper() in clean.upper() for pg in PG_PROGRAMMES)


def check_seminar_eligibility(programme: str | None) -> EligibilityResult:
    """Validate that the applicant satisfies postgraduate scope under OA-BR-61."""
    if not is_pg_student(programme):
        return EligibilityResult(
            allowed=False,
            reason="Only postgraduate (PG) students are eligible to request graduate seminar scheduling (OA-BR-61)."
        )
    return EligibilityResult(allowed=True, reason="Eligible for graduate seminar scheduling.")


def validate_seminar_request(
    topic: str,
    abstract: str,
    preferred_date: datetime.date | None = None,
    current_date: datetime.date | None = None,
) -> tuple[bool, str]:
    """Validate seminar request parameters before submission."""
    if not topic or not topic.strip():
        return False, "Seminar topic or title is required."
    if len(topic.strip()) < 5:
        return False, "Seminar topic must be at least 5 characters long."
    if not abstract or not abstract.strip():
        return False, "Seminar abstract or description is required."
    if preferred_date is not None:
        today = current_date or datetime.date.today()
        if preferred_date < today:
            return False, "Preferred seminar date cannot be in the past."
    return True, "Valid seminar request."


def validate_scheduling_parameters(
    scheduled_date: datetime.date,
    start_time: datetime.time,
    end_time: datetime.time,
    venue: str,
    current_date: datetime.date | None = None,
) -> tuple[bool, str]:
    """Validate parameters when Department Administrator schedules a seminar (OA-BR-62)."""
    today = current_date or datetime.date.today()
    if scheduled_date < today:
        return False, "Scheduled seminar date cannot be in the past."
    if start_time >= end_time:
        return False, "Seminar start time must be before end time."
    if not venue or not venue.strip():
        return False, "Venue is required for scheduling the graduate seminar."
    return True, "Valid scheduling parameters."
