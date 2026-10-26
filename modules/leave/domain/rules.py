"""Domain rules and policies for Employee Leave Management (ELM).

Implements business rules per ELM Specification v1.4:
- BR-EL-002: Casual Leave (CL) entitlement and lapse (8 days/year)
- BR-EL-003: Restricted Holiday (RH) entitlement (2 days/year)
- BR-EL-004: Special Casual Leave (SCL) entitlement (up to 15 days/year)
- BR-EL-005: Non-faculty Earned Leave (EL) credit (30 days/year, carry-forward)
- BR-EL-006: Faculty Vacation Leave (VL) entitlement (60 days/year)
- BR-EL-007: VL-to-EL year-end conversion (2:1 ratio)
- BR-EL-008: Treatment of EL created by VL conversion (carries forward)
- BR-EL-009: Commuted Leave (COL) entitlement (20 days/year, carry-forward)
- BR-EL-010: Half-day CL treatment (0.5 day)
- BR-EL-011: Continuous-day counting for EL, COL, VL
- BR-EL-012: Applicant non-overlap with half-day CL exception
- BR-EL-014: Substitute eligibility (cannot be applicant)
- BR-EL-022: Immediate withdrawal of pending request
- BR-EL-023: Cancellation of approved leave before start date
"""
from datetime import date, timedelta
from typing import Sequence


HALF_DAY_NONE = "none"
HALF_DAY_FIRST = "first_half"
HALF_DAY_SECOND = "second_half"

HALF_DAY_CHOICES = [
    (HALF_DAY_NONE, "Full Day"),
    (HALF_DAY_FIRST, "First Half"),
    (HALF_DAY_SECOND, "Second Half"),
]

CONTINUOUS_COUNTING_LEAVES = {"EL", "COL", "VL"}
CARRY_FORWARD_LEAVES = {"EL", "COL"}


def get_annual_entitlement(category_code: str, is_faculty: bool = True) -> float:
    """Returns the base annual entitlement for a given leave category and role.

    Faculty receives 60 VL (BR-EL-006); Non-faculty/staff receives 30 EL (BR-EL-005).
    """
    code = category_code.upper()
    if code == "CL":
        return 8.0
    if code == "RH":
        return 2.0
    if code == "SCL":
        return 15.0
    if code == "COL":
        return 20.0
    if code == "VL":
        return 60.0 if is_faculty else 0.0
    if code == "EL":
        return 0.0 if is_faculty else 30.0
    return 0.0


def is_carry_forward_allowed(category_code: str) -> bool:
    """Checks whether unused leave in this category carries forward (BR-EL-005, BR-EL-008, BR-EL-009)."""
    return category_code.upper() in CARRY_FORWARD_LEAVES


def calculate_leave_days(
    category_code: str,
    start_date: date,
    end_date: date,
    half_day_period: str = HALF_DAY_NONE,
) -> float:
    """Calculates requested leave days between start and end date inclusive.

    BR-EL-010: Half-day CL consumes 0.5 days.
    BR-EL-011: Continuous calendar days for EL/COL/VL; working days for CL/RH/SCL.
    """
    if start_date > end_date:
        return 0.0

    code = category_code.upper()

    # Half day CL
    if half_day_period in (HALF_DAY_FIRST, HALF_DAY_SECOND):
        if code == "CL" and start_date == end_date:
            return 0.5

    # Continuous counting for EL, COL, VL
    if code in CONTINUOUS_COUNTING_LEAVES:
        return float(max(0, (end_date - start_date).days + 1))

    # Working day counting for CL, RH, SCL (Mon-Fri)
    days = 0
    curr = start_date
    while curr <= end_date:
        if curr.weekday() < 5:
            days += 1
        curr += timedelta(days=1)
    return float(days)


def convert_vl_to_el(unused_vl: float) -> float:
    """Converts unused Vacation Leave (VL) to Earned Leave (EL) at 2:1 ratio (BR-EL-007)."""
    return round(unused_vl / 2.0, 1)


def validate_substitute(applicant_id: int, substitute_id: int | None) -> bool:
    """Validates nominated substitute (BR-EL-014: substitute cannot be applicant)."""
    if substitute_id is None:
        return True
    return applicant_id != substitute_id


def check_leave_overlap(
    existing_leaves: Sequence[dict],
    new_start: date,
    new_end: date,
    new_half_day: str = HALF_DAY_NONE,
) -> bool:
    """Validates non-overlap with active leave requests (BR-EL-012).

    Exception: First-half and second-half CL on the same date do not overlap.
    """
    for leave in existing_leaves:
        ex_start = leave["start_date"]
        ex_end = leave["end_date"]
        ex_half = leave.get("half_day_period", HALF_DAY_NONE)

        if max(new_start, ex_start) <= min(new_end, ex_end):
            # Check half-day CL exception on same single day
            if (
                new_start == new_end == ex_start == ex_end
                and new_half_day in (HALF_DAY_FIRST, HALF_DAY_SECOND)
                and ex_half in (HALF_DAY_FIRST, HALF_DAY_SECOND)
            ):
                if new_half_day != ex_half:
                    continue
            return True
    return False


def can_cancel_leave(leave_start_date: date, today: date) -> bool:
    """Approved leave may only be cancelled before its start date (BR-EL-023)."""
    return today < leave_start_date
