"""Pure Python business rules for Employee Leave Management.

No Django, DRF or Celery imports allowed in domain/.
"""
from datetime import date, timedelta


CONTINUOUS_COUNT_LEAVES = {"EL", "COL", "VL"}


def calculate_leave_days(leave_type: str, start_date: date, end_date: date, half_day: bool = False) -> float:
    """Calculate effective leave days according to leave rules.

    EL, COL, and VL use continuous-count across the approved interval.
    CL, SCL, and RH do not count weekends in standard calculation.
    Half-day CL consumes 0.5 days.
    """
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")

    if half_day:
        if leave_type != "CL":
            raise ValueError("Half-day leave is only permitted for Casual Leave (CL)")
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
    """An applicant cannot nominate themselves as substitute."""
    if substitute_id is not None and applicant_id == substitute_id:
        raise ValueError("Applicant cannot nominate themselves as substitute")
