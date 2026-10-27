"""
Leave Policy Rules (BR-EL-001..015).
Pure Python implementation without Django/DRF/Celery imports.
"""

from datetime import date, timedelta
from decimal import Decimal


class PolicyError(Exception):
    """Domain policy error."""



CATEGORIES = ("CL", "RH", "SCL", "EL", "COL", "VL")

ENTITLEMENT: dict[str, tuple] = {
    "CL": (Decimal("8"), True, True, False),  # BR-EL-002
    "RH": (Decimal("2"), True, True, False),  # BR-EL-003
    "SCL": (Decimal("15"), True, True, False),  # BR-EL-004
    "EL": (Decimal("30"), False, True, True),  # BR-EL-005
    "COL": (Decimal("20"), True, True, True),  # BR-EL-009
    "VL": (Decimal("60"), True, False, False),  # BR-EL-006
}

CONTINUOUS = {"EL", "COL", "VL"}


def entitlement(category: str, kind: str) -> Decimal | None:
    """
    Return the annual leave entitlement for a category and kind.

    - kind="faculty" returns faculty allowance (or None if not eligible).
    - Any other kind (e.g., "staff", "employee", "") is treated as staff.
    - Returns None if the category is not supported or the user kind is ineligible.

    BR-EL-001: Only supported categories allowed.
    BR-EL-005: EL is for non-faculty only (faculty_allowed=False).
    """
    if category not in CATEGORIES:
        raise PolicyError(f"Unknown leave category: {category}")  # BR-EL-001

    days_per_year, faculty_allowed, staff_allowed, _carries_forward = ENTITLEMENT[category]

    is_faculty = kind == "faculty"

    if is_faculty:
        if faculty_allowed:
            return days_per_year
        return None  # EL is not for faculty
    # Any kind other than "faculty" is treated as staff
    if staff_allowed:
        return days_per_year
    return None  # VL is not for staff (faculty_allowed=True, staff_allowed=False)


def count_days(category: str, start: date, end: date, half_day: str = "none") -> Decimal:
    """
    Calculate the number of leave days consumed.

    BR-EL-010: Half-day CL consumes 0.5 day (only for CL and when start==end).
    BR-EL-011: EL, COL, VL count every calendar day inclusive (weekends/holidays included).
               CL, RH, SCL count Monday to Friday only.

    Note: Since no external calendar service is imported, we assume the input dates represent
    the requested interval. For CL/RH/SCL, we will perform a basic weekday check assuming
    standard work weeks (Mon-Fri) as per BR-EL-011 implication for non-continuous categories.
    """
    if start > end:
        raise PolicyError("End date must be on or after start date")  # Generic validation

    if half_day != "none" and category not in ("CL",):
        raise PolicyError(
            f"Half-day consumption only applies to CL. Category: {category}"
        )  # BR-EL-010

    if half_day != "none" and start != end:
        raise PolicyError("Half-day consumption only allowed for single-day requests")  # BR-EL-010

    category_upper = category.upper()

    if category_upper in CONTINUOUS:
        # BR-EL-011: EL, COL, VL count every calendar day inclusive.
        # No filtering for weekends/holidays.
        days = Decimal(str((end - start).days + 1))
    else:
        # CL, RH, SCL: Count Monday to Friday only.
        # Since no holiday calendar is available, we assume standard working days (Mon-Fri).
        days = Decimal("0")
        current = start
        while current <= end:
            if current.weekday() < 5:  # Monday=0 to Friday=4
                days += Decimal("1")
            current += timedelta(days=1)

    if half_day != "none":
        # Apply half-day consumption (0.5 day) directly per BR-EL-010
        return Decimal("0.5")

    return days


def overlaps(
    a_start: date, a_end: date, a_half: str, b_start: date, b_end: date, b_half: str
) -> bool:
    """
    Check if two leave requests overlap.

    True when the date ranges intersect.
    Exception: A single shared date where both halves are set
    and different does not count as overlap.
    BR-EL-012: Applicant non-overlap with half-day CL exception.
    """
    # Determine if ranges intersect
    # Intersection exists if: start_a <= end_b AND start_b <= end_a
    intersects = (a_start <= b_end) and (b_start <= a_end)

    if not intersects:
        return False

    # Check for the half-day exception on the same date
    # Exception applies only to CL (implied by context of BR-EL-012 regarding halves)
    # If both are on the same day and have different halves, they do NOT overlap.
    # Different halves of the same day do not overlap (BR-EL-012)
    return not (
        a_start == b_start
        and a_half != "none"
        and b_half != "none"
        and a_half != b_half
    )


def unit_head_is_final(category: str) -> bool:
    """
    Determine if Unit Head has final decision power.

    BR-EL-016: True for CL and RH.
    BR-EL-017: Others only get a recommendation.
    """
    return category in ("CL", "RH")
