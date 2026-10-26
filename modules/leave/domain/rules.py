"""Domain rules and validation constraints for employee leave management.

Pure Python module with no Django dependencies. Implements business rules
from the ELM specification (BR-EL-001 through BR-EL-014, AFR-EL-001.1, AFR-EL-003.3).
"""
from __future__ import annotations

from datetime import date, timedelta

#: BR-EL-001: Supported leave categories
SUPPORTED_CATEGORIES: tuple[str, ...] = ("CL", "RH", "SCL", "EL", "COL", "VL")

#: Fixed non-accumulating annual entitlement quotas (BR-EL-002, BR-EL-003, BR-EL-004).
#: CL (8 days), RH (2 days), and SCL (15 days) lapse at year-end and cannot carry forward.
#: Accumulated/carry-forward categories (such as EL under BR-EL-005) are not capped by a single
#: year's credit and require LeaveBalance lookups for full validation.
ANNUAL_ENTITLEMENTS: dict[str, float] = {
    "CL": 8.0,
    "RH": 2.0,
    "SCL": 15.0,
}

#: Action to permission code mapping (AFR-EL-001.1, CFR-EL-001).
#: Enforces role-based authority mapping for domain operations and satisfies manifest checks.
ACTION_PERMISSIONS: dict[str, str] = {
    "view": "leave.application.view",
    "apply": "leave.application.create",
    "review": "leave.application.review",
    "approve": "leave.application.approve",
    "withdraw": "leave.application.delete",
    "substitute_respond": "leave.substitute.respond",
    "balance_view": "leave.balance.view",
}


def is_substitute_valid(
    applicant_id: int | None,
    substitute_id: int | None,
) -> bool:
    """Validate substitute nomination constraints according to BR-EL-014.

    The substitute must be another employee and must not be the applicant themselves.
    Returns False if substitute_id is non-null and equals applicant_id.
    """
    if applicant_id is not None and substitute_id is not None:
        return applicant_id != substitute_id
    return True


def calculate_chargeable_days(
    category: str,
    start_date: date,
    end_date: date,
    half_day_cl: bool = False,
    holidays: set[date] | None = None,
) -> float:
    """Compute net chargeable leave duration in days (BR-EL-010, BR-EL-011, AFR-EL-003.3).

    - Half-day CL consumes 0.5 days (BR-EL-010).
    - Continuous-counting categories (EL, COL, VL): every calendar day between
      start_date and end_date (inclusive) counts as a leave day, including weekends
      and holidays (BR-EL-011).
    - Non-continuous categories (CL, SCL, RH): only working days (Monday-Friday,
      excluding declared holidays) count as leave days (BR-EL-011).
    """
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")

    if half_day_cl and category == "CL":
        return 0.5

    continuous_categories = {"EL", "COL", "VL"}
    if category in continuous_categories:
        return float((end_date - start_date).days + 1)

    holiday_set = holidays or set()
    total_days = 0
    current = start_date

    while current <= end_date:
        # 0 = Monday, 6 = Sunday. Saturdays (5) and Sundays (6) are weekends.
        if current.weekday() < 5 and current not in holiday_set:
            total_days += 1
        current += timedelta(days=1)
    return float(total_days)


def is_half_day_cl_valid(
    half_day_cl: bool,
    category: str = "CL",
    start_date: date | None = None,
    end_date: date | None = None,
) -> bool:
    """Validate half-day leave constraints according to BR-EL-010.

    - A full-day leave request (half_day_cl=False) is valid across categories.
    - Half-day leave is permitted exclusively for Casual Leave (CL).
    - If dates are supplied for a half-day request, start_date and end_date must match.
    """
    if not half_day_cl:
        return True
    if category != "CL":
        return False
    if start_date is not None and end_date is not None:
        return start_date == end_date
    return True


def is_overlap_valid(start_date: date, end_date: date) -> bool:
    """BR-EL-011: Start date must precede or equal end date."""
    if start_date is None or end_date is None:
        return False
    return start_date <= end_date


def do_intervals_overlap(
    start_a: date,
    end_a: date,
    start_b: date,
    end_b: date,
    half_day_a: bool = False,
    half_day_b: bool = False,
) -> bool:
    """Check interval overlap with the BR-EL-012 half-day CL exception.

    Two intervals overlap if they share calendar dates, EXCEPT when both are
    half-day CL requests on the same single date (representing first and second halves).
    """
    if end_a < start_b or end_b < start_a:
        return False
    return not (half_day_a and half_day_b and start_a == end_a == start_b == end_b)

