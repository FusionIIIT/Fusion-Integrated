"""Pure Python business rules for Employee Leave Management.

No Django, DRF or Celery imports allowed in domain/.
"""
from datetime import date, timedelta

CONTINUOUS_COUNT_LEAVES = {"EL", "COL", "VL"}


def calculate_leave_days(
    leave_type: str,
    start_date: date,
    end_date: date,
    half_day: bool = False,
) -> float:
    """Calculate effective leave days according to leave rules.

    EL, COL, and VL use continuous-count across the approved interval (BR-EL-011).
    CL, SCL, and RH do not count weekends in standard calculation (BR-EL-011).
    Half-day CL consumes 0.5 days on a single date (BR-EL-010).
    """
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")

    if half_day:
        if leave_type != "CL":
            raise ValueError("Half-day leave is only permitted for Casual Leave (CL)")
        if start_date != end_date:
            raise ValueError("Half-day leave must be for a single date")
        return 0.5

    if leave_type in CONTINUOUS_COUNT_LEAVES:
        return float((end_date - start_date).days + 1)

    # For CL, SCL, RH: exclude weekends (Saturday=5, Sunday=6)
    days = 0
    cur = start_date
    while cur <= end_date:
        if cur.weekday() < 5:
            days += 1
        cur += timedelta(days=1)
    return float(days)


def validate_substitute(applicant_id: int, substitute_id: int | None) -> None:
    """An applicant cannot nominate themselves as substitute (BR-EL-014)."""
    if substitute_id is not None and applicant_id == substitute_id:
        raise ValueError("Applicant cannot nominate themselves as substitute")


def is_date_overlap(
    start1: date,
    end1: date,
    start2: date,
    end2: date,
    half_day1: bool = False,
    half_type1: str = "",
    half_day2: bool = False,
    half_type2: str = "",
) -> bool:
    """Check if two leave applications overlap.

    Per BR-EL-012: First-half and second-half CL on the same date are not
    treated as overlapping when they occupy different halves.
    """
    if start1 > end2 or end1 < start2:
        return False

    # Check half-day exception on the same date
    is_non_overlapping_half = (
        start1 == end1 == start2 == end2
        and half_day1
        and half_day2
        and bool(half_type1)
        and bool(half_type2)
        and half_type1 != half_type2
    )
    return not is_non_overlapping_half
