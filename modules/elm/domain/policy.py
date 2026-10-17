"""Leave policy from the ELM Business Rule Specifications v1.4.

Each function names the rule it implements. Holidays are passed in rather than
looked up: the holiday/RH calendar (BR-EL-031) is not modelled yet, so callers
supply whatever closed dates they know about.
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta
from decimal import Decimal

from .entities import (
    CONTINUOUS,
    Balance,
    LeaveCategory,
    LeaveSpan,
)
from .errors import (
    IneligibleCategory,
    InsufficientBalance,
    InvalidDateRange,
    MissingStationDetails,
    OverlappingLeave,
)

EMPLOYEE_KINDS = frozenset({"faculty", "staff"})

#: Days credited per calendar year (BR-EL-002 to BR-EL-006, BR-EL-009).
ANNUAL_ENTITLEMENT: dict[LeaveCategory, Decimal] = {
    LeaveCategory.CL: Decimal(8),
    LeaveCategory.RH: Decimal(2),
    LeaveCategory.SCL: Decimal(15),
    LeaveCategory.EL: Decimal(30),     # non-faculty only; see entitlement_for
    LeaveCategory.COL: Decimal(20),
    LeaveCategory.VL: Decimal(60),     # faculty only
}


def entitlement_for(category: LeaveCategory, kind: str) -> Decimal:
    """Faculty earn no EL directly; theirs comes from VL conversion (BR-EL-007/008).
    Non-faculty hold no VL (BR-EL-006)."""
    if kind not in EMPLOYEE_KINDS:
        return Decimal(0)
    if category == LeaveCategory.EL and kind == "faculty":
        return Decimal(0)
    if category == LeaveCategory.VL and kind != "faculty":
        return Decimal(0)
    return ANNUAL_ENTITLEMENT[category]


def check_eligibility(category: LeaveCategory, kind: str) -> None:
    """BR-EL-001: only employees apply, and VL is for faculty alone."""
    if kind not in EMPLOYEE_KINDS:
        raise IneligibleCategory("Only faculty and staff can apply for leave.")
    if category == LeaveCategory.VL and kind != "faculty":
        raise IneligibleCategory("Vacation Leave is available to faculty only.")


def count_days(category: LeaveCategory, span: LeaveSpan,
               holidays: Iterable[date] = ()) -> Decimal:
    """How many days a span consumes.

    BR-EL-010: a half-day CL is 0.5.
    BR-EL-011: EL/COL/VL count every calendar day in the interval; CL, SCL and
    RH skip weekends and closed holidays.
    """
    if span.end < span.start:
        raise InvalidDateRange("The end date cannot be before the start date.")
    if span.half:
        if category != LeaveCategory.CL:
            raise InvalidDateRange("Only Casual Leave can be taken as a half day.")
        if span.start != span.end:
            raise InvalidDateRange("A half-day leave must start and end on the same date.")
        return Decimal("0.5")

    total = (span.end - span.start).days + 1
    if category in CONTINUOUS:
        return Decimal(total)

    closed = set(holidays)
    working = sum(
        1 for i in range(total)
        if (d := span.start + timedelta(days=i)).weekday() < 5 and d not in closed)
    if working == 0:
        raise InvalidDateRange("The selected dates contain no working day.")
    return Decimal(working)


def check_balance(balance: Balance, days: Decimal) -> None:
    if days > balance.available:
        raise InsufficientBalance(
            f"{balance.category} balance is {balance.available} day(s); "
            f"this request needs {days}.")


def check_no_overlap(span: LeaveSpan, existing: Iterable[LeaveSpan]) -> None:
    """BR-EL-012, against the applicant's pending and approved leave."""
    for other in existing:
        if span.overlaps(other):
            raise OverlappingLeave(
                f"These dates overlap your leave from {other.start} to {other.end}.")


def check_station_details(is_station_leave: bool, address: str, contact: str) -> None:
    """BR-EL-013: Station Leave lives inside the same application, so its
    details are required with it rather than in a separate request."""
    if is_station_leave and not (address.strip() and contact.strip()):
        raise MissingStationDetails(
            "Station Leave needs the address and contact number while away.")


def validate_new_request(*, category: LeaveCategory, kind: str, span: LeaveSpan,
                         balance: Balance, existing: Iterable[LeaveSpan],
                         is_station_leave: bool = False, station_address: str = "",
                         station_contact: str = "",
                         holidays: Iterable[date] = ()) -> Decimal:
    """Every check a new request must pass, in the order a user would want to
    hear about them. Returns the number of days the request consumes."""
    check_eligibility(category, kind)
    if span.start.year != span.end.year:
        raise InvalidDateRange(
            "A request cannot cross a calendar year; split it into two requests.")
    days = count_days(category, span, holidays)
    check_no_overlap(span, existing)
    check_balance(balance, days)
    check_station_details(is_station_leave, station_address, station_contact)
    return days


__all__ = [
    "ANNUAL_ENTITLEMENT", "EMPLOYEE_KINDS", "check_balance",
    "check_eligibility", "check_no_overlap", "check_station_details",
    "count_days", "entitlement_for", "validate_new_request",
]
