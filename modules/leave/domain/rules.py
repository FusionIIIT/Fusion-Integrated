"""ELM policy, counting and routing. Pure Python — no Django in here.

    BR-EL-002..009   entitlement per category
    BR-EL-010..011   half-day CL, continuous counting
    BR-EL-012        overlap, with the half-day CL exception
    BR-EL-016..020   who decides, and in what order
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

#: Annual entitlement by category. VL is faculty-only, EL non-faculty-only.
ENTITLEMENT = {
    "CL": Decimal("8"),
    "RH": Decimal("2"),
    "SCL": Decimal("15"),
    "EL": Decimal("30"),
    "COL": Decimal("20"),
    "VL": Decimal("60"),
}

#: Unused balance that survives the year-end boundary (BR-EL-005, BR-EL-009).
CARRY_FORWARD = {"EL", "COL"}

#: Weekends and closed holidays inside the interval count as leave (BR-EL-011).
CONTINUOUS_COUNT = {"EL", "COL", "VL"}

#: The Unit Head is the final authority for these (BR-EL-016).
UNIT_HEAD_FINAL = {"CL", "RH"}

#: Categories an ongoing leave may be extended or resumed against.
EXTENDABLE = {"EL", "COL", "VL"}

FACULTY_ONLY = {"VL"}
NON_FACULTY_ONLY = {"EL"}

#: VL → EL at year end, 2 VL : 1 EL including the fraction (BR-EL-007).
VL_TO_EL_RATIO = Decimal("2")

#: Resolved path after the Unit Head's recommendation (BR-EL-018, BR-EL-019).
AUTHORITY_CHAIN = {
    "SCL": ["Deputy Registrar (Estt.)", "Registrar"],
    "EL": ["Deputy Registrar (Estt.)", "Registrar"],
    "COL": ["Deputy Registrar (Estt.)", "Registrar"],
    "VL": ["Dean", "Director"],
}

DIRECTOR_DESIGNATION = "Director"


class RuleViolation(Exception):
    """A spec rule said no. Carries the rule id so the message can cite it."""

    def __init__(self, message: str, rule: str = ""):
        super().__init__(message)
        self.message = message
        self.rule = rule


def entitlement_for(leave_type: str, employee_kind: str) -> Decimal:
    """BR-EL-001: the category must apply to this kind of employee at all."""
    faculty = employee_kind == "faculty"
    if leave_type in FACULTY_ONLY and not faculty:
        raise RuleViolation(f"{leave_type} applies to faculty only.", "BR-EL-006")
    if leave_type in NON_FACULTY_ONLY and faculty:
        raise RuleViolation(f"{leave_type} applies to non-faculty employees only.",
                            "BR-EL-005")
    if leave_type not in ENTITLEMENT:
        raise RuleViolation(f"{leave_type} is not a supported category.", "BR-EL-001")
    return ENTITLEMENT[leave_type]


def count_days(leave_type: str, start: date, end: date, half_day: str,
               closed_dates: set[date]) -> Decimal:
    """Leave days for the requested interval.

    EL/COL/VL count every intervening day including weekends and closed
    holidays. CL/SCL/RH skip them, and a half-day CL consumes 0.5.
    """
    if end < start:
        raise RuleViolation("The end date cannot be before the start date.",
                            "BR-EL-011")
    if half_day:
        if leave_type != "CL":
            raise RuleViolation("Only Casual Leave supports a half day.", "BR-EL-010")
        if start != end:
            raise RuleViolation("A half-day request covers a single date.",
                                "BR-EL-010")
        return Decimal("0.5")

    total = Decimal("0")
    day = start
    while day <= end:
        counts = (leave_type in CONTINUOUS_COUNT
                  or (day.weekday() < 5 and day not in closed_dates))
        if counts:
            total += Decimal("1")
        day += timedelta(days=1)
    return total


def overlaps(a_start: date, a_end: date, a_half: str,
             b_start: date, b_end: date, b_half: str) -> bool:
    """BR-EL-012. First-half and second-half CL on one date do not collide."""
    if a_end < b_start or b_end < a_start:
        return False
    return not (a_half and b_half and a_half != b_half)


def resolve_chain(leave_type: str, applicant_designation: str) -> list[str]:
    """The steps after the Unit Head, in order.

    BR-EL-020: the Director's own leave is self-sanctioned, so no step follows.
    """
    if applicant_designation == DIRECTOR_DESIGNATION:
        return []
    if leave_type in UNIT_HEAD_FINAL:
        return []
    return list(AUTHORITY_CHAIN.get(leave_type, ["Registrar"]))


def vl_conversion(unused_vl: Decimal) -> Decimal:
    """BR-EL-007: fractional conversion is kept, not rounded away."""
    return (unused_vl / VL_TO_EL_RATIO).quantize(Decimal("0.1"))


def year_end_outcome(leave_type: str) -> str:
    """BR-EL-002..009, read by the year-end job."""
    if leave_type == "VL":
        return "convert_to_el"
    if leave_type in CARRY_FORWARD:
        return "carry_forward"
    return "lapse"
