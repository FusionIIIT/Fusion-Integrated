"""Pure business rules for Employee Leave Management."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum


class LeaveType(StrEnum):
    CL = "CL"
    RH = "RH"
    SCL = "SCL"
    EL = "EL"
    COL = "COL"
    VL = "VL"


ANNUAL_ENTITLEMENTS: dict[LeaveType, int] = {
    LeaveType.CL: 8,
    LeaveType.RH: 2,
    LeaveType.SCL: 15,
    LeaveType.EL: 30,   # canonical non-faculty entitlement
    LeaveType.COL: 20,
    # VL is associated with published faculty vacation periods.
}


class LeaveRuleError(ValueError):
    """Raised when a leave request violates a domain rule."""


@dataclass(frozen=True)
class LeavePeriod:
    start: date
    end: date
    leave_type: LeaveType
    half_day: str | None = None

    def __post_init__(self) -> None:
        validate_period(self.start, self.end, self.leave_type, self.half_day)


def validate_period(
    start: date,
    end: date,
    leave_type: LeaveType,
    half_day: str | None = None,
) -> None:
    """Validate dates and the half-day exception for Casual Leave."""
    if end < start:
        raise LeaveRuleError("End date must be on or after start date.")

    if half_day is not None:
        if leave_type != LeaveType.CL:
            raise LeaveRuleError("Half-day requests are supported only for CL.")
        if start != end:
            raise LeaveRuleError("A half-day request must cover exactly one date.")
        if half_day not in {"first", "second"}:
            raise LeaveRuleError("half_day must be 'first' or 'second'.")


def periods_overlap(first: LeavePeriod, second: LeavePeriod) -> bool:
    """Return whether two periods conflict, including half-day CL requests."""
    if first.end < second.start or second.end < first.start:
        return False

    same_single_day = first.start == first.end == second.start == second.end
    if (
        same_single_day
        and first.leave_type == second.leave_type == LeaveType.CL
        and first.half_day is not None
        and second.half_day is not None
    ):
        return first.half_day == second.half_day

    return True


def entitlement_for(leave_type: LeaveType, *, is_faculty: bool = False) -> int | None:
    """Return the canonical annual entitlement, or None when policy-dependent."""
    if leave_type == LeaveType.VL:
        return 60 if is_faculty else None
    if leave_type == LeaveType.EL and is_faculty:
        return None
    return ANNUAL_ENTITLEMENTS.get(leave_type)


def calculate_leave_days(
    start: date,
    end: date,
    leave_type: LeaveType,
    *,
    working_weekdays: set[int] | frozenset[int],
    closed_holidays: set[date] | None = None,
    half_day: str | None = None,
) -> float:
    """Calculate chargeable leave days using the supplied working calendar."""
    validate_period(start, end, leave_type, half_day)
    holidays = closed_holidays or set()

    if half_day is not None:
        if start.weekday() not in working_weekdays or start in holidays:
            return 0.0
        return 0.5

    if leave_type in {LeaveType.EL, LeaveType.COL, LeaveType.VL}:
        return float((end - start).days + 1)

    days = 0
    current = start
    while current <= end:
        if current.weekday() in working_weekdays and current not in holidays:
            days += 1
        current += timedelta(days=1)

    return float(days)


def convert_unused_vl_to_el(unused_vl: float) -> float:
    """Convert unused VL to EL at the canonical 2:1 ratio."""
    if unused_vl < 0:
        raise LeaveRuleError("Unused VL cannot be negative.")
    return unused_vl / 2
