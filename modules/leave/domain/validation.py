"""Eligibility, calendar and overlap validation (BR-EL-001…014, CFR-EL-003).

Pure functions over dates and plain data. Calendar rows and balances are
injected, so every rule here is testable with no database and the service
stays the only place that knows where those come from.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from modules.leave.domain.categories import (
    CL,
    FACULTY_ONLY_CATEGORIES,
    HALF_DAY_CATEGORIES,
    HALF_FIRST,
    HALF_SECOND,
)
from modules.leave.domain.counting import daterange


class ValidationError(Exception):
    """A rule refused the request. `code` is machine-readable for the API."""

    def __init__(self, message: str, *, code: str = "invalid_request"):
        super().__init__(message)
        self.message = message
        self.code = code


def check_category_applicable(*, category: str, is_faculty: bool) -> None:
    """BR-EL-001 / BR-EL-006: category applicability for this employee."""
    if category in FACULTY_ONLY_CATEGORIES and not is_faculty:
        raise ValidationError(
            "Vacation Leave is available to faculty only.",
            code="category_not_applicable")


def check_interval(*, start: date, end: date, half_day: str,
                   category: str) -> None:
    if end < start:
        raise ValidationError("The end date is before the start date.",
                              code="invalid_interval")
    if half_day not in (HALF_FIRST, HALF_SECOND, "none"):
        raise ValidationError("Unknown half-day value.", code="invalid_half_day")
    if half_day != "none":
        if category not in HALF_DAY_CATEGORIES:
            raise ValidationError(
                "Half-day leave is supported only for Casual Leave.",
                code="half_day_not_supported")
        if start != end:
            raise ValidationError(
                "A half-day leave must be a single day.",
                code="half_day_must_be_single_day")


def check_rh_calendar(*, start: date, end: date,
                      restricted_dates: set[date]) -> None:
    """BR-EL-003 / CFR-EL-005.2: every requested RH date must be an
    applicable Restricted Holiday in the currently effective published
    holiday/RH calendar (BR-EL-031)."""
    for d in daterange(start, end):
        if d not in restricted_dates:
            raise ValidationError(
                f"{d.isoformat()} is not a Restricted Holiday in the "
                f"currently effective published calendar.",
                code="rh_not_applicable")


def check_vl_vacation_period(*, start: date, end: date,
                             vacation_periods: list[tuple[date, date]]) -> None:
    """BR-EL-006 / CFR-EL-008.3: VL may be availed only during an applicable
    vacation period supplied through the Academic Calendar (EXT-01)."""
    for d in daterange(start, end):
        if not any(v_start <= d <= v_end for v_start, v_end in vacation_periods):
            raise ValidationError(
                "Vacation Leave may only be taken during a published "
                f"vacation period; {d.isoformat()} is outside every one.",
                code="vl_outside_vacation")


class Interval:
    """One existing leave interval, for overlap checks."""

    __slots__ = ("start", "end", "half_day", "category")

    def __init__(self, start: date, end: date, half_day: str, category: str):
        self.start, self.end = start, end
        self.half_day, self.category = half_day, category

    def dates(self) -> list[date]:
        return daterange(self.start, self.end)


def _overlaps(a: Interval, b: Interval) -> bool:
    if a.end < b.start or b.end < a.start:
        return False
    # BR-EL-012: first-half and second-half CL on the same date occupy
    # different halves and are therefore NOT overlapping.
    same_day = a.start == a.end == b.start == b.end
    if (same_day and a.category == CL and b.category == CL
            and a.half_day in (HALF_FIRST, HALF_SECOND)
            and b.half_day in (HALF_FIRST, HALF_SECOND)
            and a.half_day != b.half_day):
        return False
    return True


def intervals_overlap(a: Interval, b: Interval) -> bool:
    return _overlaps(a, b)


def check_overlap(*, start: date, end: date, half_day: str, category: str,
                  existing: list[Interval]) -> None:
    """BR-EL-012 / CFR-EL-003.4: a new request may not impermissibly overlap
    the employee's active pending or approved leave."""
    new = Interval(start, end, half_day, category)
    for other in existing:
        if _overlaps(new, other):
            raise ValidationError(
                "This request overlaps existing pending or approved leave "
                f"from {other.start.isoformat()} to {other.end.isoformat()}.",
                code="overlapping_leave")


def check_balance(*, available: Decimal, required: Decimal,
                  category: str) -> None:
    """BR-EL-002…009: insufficient entitlement/balance blocks progression."""
    if required <= 0:
        raise ValidationError(
            "This request consumes no leave days; check the dates.",
            code="zero_chargeable_days")
    if available < required:
        raise ValidationError(
            f"Insufficient {category.upper()} balance: {available} day(s) "
            f"available, {required} requested.",
            code="insufficient_balance")


def check_substitute(*, nominee: int, applicant: int,
                     employee_ids: set[int]) -> None:
    """BR-EL-014 / CFR-EL-011: another employee, not the applicant, who is a
    member of the directory. Their own overlapping leave is checked by the
    caller, which owns the responsibility period's dates."""
    if nominee == applicant:
        raise ValidationError("The substitute cannot be the applicant.",
                              code="self_substitute")
    if nominee not in employee_ids:
        raise ValidationError("The substitute must be an employee.",
                              code="substitute_not_employee")
