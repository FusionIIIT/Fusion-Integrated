"""Leave categories, entitlements, day-counting and conversion rules.

Pure functions and frozen data — the leave-policy baseline from the ELM problem
statement (PS v1.4 sections 3-4). These are the numbers the rest of the module trusts,
kept here so they are readable in one place and testable without a database.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum


class LeaveCategory(StrEnum):
    CL = "cl"          # Casual Leave
    RH = "rh"          # Restricted Holiday
    SCL = "scl"        # Special Casual Leave
    EL = "el"          # Earned Leave
    COL = "col"        # Commuted Leave (medical)
    VL = "vl"          # Vacation Leave (faculty only)

    @property
    def label(self) -> str:
        return _LABELS[self]


_LABELS = {
    LeaveCategory.CL: "Casual Leave",
    LeaveCategory.RH: "Restricted Holiday",
    LeaveCategory.SCL: "Special Casual Leave",
    LeaveCategory.EL: "Earned Leave",
    LeaveCategory.COL: "Commuted Leave",
    LeaveCategory.VL: "Vacation Leave",
}

#: Annual entitlement per category. EL/VL depend on whether the employee is
#: faculty, so those two carry a callable instead of a flat number.
_ENTITLEMENT: dict[LeaveCategory, int] = {
    LeaveCategory.CL: 8,
    LeaveCategory.RH: 2,
    LeaveCategory.SCL: 15,
    LeaveCategory.COL: 20,
}

#: Categories whose unused balance carries forward into the next year.
_CARRIES_FORWARD = {LeaveCategory.EL, LeaveCategory.COL}

#: Categories counted continuously: every calendar day in the interval,
#: including weekends and closed holidays, is a leave day (PS §4).
_CONTINUOUS = {LeaveCategory.EL, LeaveCategory.COL, LeaveCategory.VL}

#: Only CL supports a first-half / second-half request (PS §3).
_HALF_DAY_CAPABLE = {LeaveCategory.CL}

#: Faculty members earn VL; everyone else (staff and non-faculty) earns EL.
FACULTY_VL_ENTITLEMENT = 60
NON_FACULTY_EL_ENTITLEMENT = 30

#: Year-end VL -> EL ratio: 2 days of unused VL become 1 day of EL (PS §3).
VL_TO_EL_DENOMINATOR = Decimal("2")

DEFAULT_WEEKEND_DAYS = (5, 6)   # Saturday, Sunday (datetime.weekday())


def entitlement(category: LeaveCategory, *, kind: str) -> Decimal:
    """Annual entitlement for one employee of the given kind."""
    if category == LeaveCategory.EL:
        return (Decimal("0") if kind == "faculty"
                else Decimal(NON_FACULTY_EL_ENTITLEMENT))
    if category == LeaveCategory.VL:
        return (Decimal(FACULTY_VL_ENTITLEMENT) if kind == "faculty"
                else Decimal("0"))
    return Decimal(_ENTITLEMENT[category])


def carries_forward(category: LeaveCategory) -> bool:
    return category in _CARRIES_FORWARD


def is_continuous(category: LeaveCategory) -> bool:
    return category in _CONTINUOUS


def supports_half_day(category: LeaveCategory) -> bool:
    return category in _HALF_DAY_CAPABLE


def count_days(category: LeaveCategory, start: date, end: date, *,
               half: str = "full", holidays: frozenset[date] = frozenset(),
               weekend_days: tuple[int, ...] = DEFAULT_WEEKEND_DAYS) -> Decimal:
    """Chargeable leave days for an interval.

    - Continuous categories (EL/COL/VL) charge every calendar day, weekends and
      holidays included.
    - CL/SCL/RH skip weekends and closed holidays.
    - A half-day CL charges 0.5, regardless of which half.
    """
    if end < start:
        raise ValueError("end date precedes start date")

    if half != "full" and not supports_half_day(category):
        raise ValueError(f"{category.label} does not support half-day requests")

    if is_continuous(category):
        days = (end - start).days + 1
    else:
        days = _working_days(start, end, holidays, weekend_days)

    if half != "full":
        return Decimal("0.5")
    return Decimal(days)


def _working_days(start: date, end: date, holidays: frozenset[date],
                  weekend_days: tuple[int, ...]) -> int:
    n = 0
    d = start
    while d <= end:
        if d.weekday() not in weekend_days and d not in holidays:
            n += 1
        d += timedelta(days=1)
    return n


def overlaps(a_start: date, a_end: date, a_half: str,
             b_start: date, b_end: date, b_half: str) -> bool:
    """Do two leave intervals overlap?

    First-half and second-half CL on the same date are NOT overlapping when
    they occupy different halves (PS §5 / AFR-EL-003.5).
    """
    if a_end < b_start or b_end < a_start:
        return False
    # Same day, both half-day, different halves -> not overlapping.
    return not (a_start == b_start == a_end == b_end and a_half != b_half)


def convert_vl_to_el(vl_remaining: Decimal) -> Decimal:
    """Year-end conversion: 2 VL -> 1 EL, fractions preserved (PS §3)."""
    return vl_remaining / VL_TO_EL_DENOMINATOR
