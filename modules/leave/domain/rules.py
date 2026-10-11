"""Domain rules and validation constraints for employee leave management.

Pure Python module with no Django dependencies. Implements business rules
from the ELM specification (BR-EL-001, BR-EL-010, BR-EL-011, BR-EL-012).
"""
from __future__ import annotations

from datetime import date

#: BR-EL-001: Supported leave categories
SUPPORTED_CATEGORIES: tuple[str, ...] = ("CL", "RH", "SCL", "EL", "COL", "VL")

#: Annual entitlement quotas by category (BR-EL-002, BR-EL-003, BR-EL-004, BR-EL-005)
ANNUAL_ENTITLEMENTS: dict[str, float] = {
    "CL": 8.0,
    "RH": 2.0,
    "SCL": 15.0,
    "EL": 30.0,
}


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

