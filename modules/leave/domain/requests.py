"""Rules for the deliberately narrow leave-request foundation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


class LeaveRuleError(ValueError):
    """A request violates a leave rule before it reaches persistence."""


VALID_HALF_DAYS = frozenset({"full", "first", "second"})


@dataclass(frozen=True)
class RequestPeriod:
    category: str
    starts_on: date
    ends_on: date
    cl_half: str


def validate_period(period: RequestPeriod) -> None:
    if period.category not in {"cl", "rh"}:
        raise LeaveRuleError("Only CL and RH are available in this foundation.")
    if period.ends_on < period.starts_on:
        raise LeaveRuleError("The leave end date cannot be before the start date.")
    if period.cl_half not in VALID_HALF_DAYS:
        raise LeaveRuleError("The leave half-day value is invalid.")
    if period.category != "cl" and period.cl_half != "full":
        raise LeaveRuleError("Only CL can be requested as a half day.")
    if period.cl_half != "full" and period.starts_on != period.ends_on:
        raise LeaveRuleError("A half-day CL request must cover one date.")


def validate_request(*, period: RequestPeriod, reason: str, station_leave: bool,
                     station_leave_details: str) -> None:
    """Validate data common to every leave-request write boundary."""
    validate_period(period)
    if not reason.strip():
        raise LeaveRuleError("A leave reason is required.")
    if station_leave and not station_leave_details.strip():
        raise LeaveRuleError("Station Leave details are required.")


def overlaps(left: RequestPeriod, right: RequestPeriod) -> bool:
    """Whether two pending requests conflict.

    First- and second-half CL on exactly the same date are explicitly allowed.
    """
    if left.ends_on < right.starts_on or right.ends_on < left.starts_on:
        return False
    same_day_halves = (
        left.category == right.category == "cl"
        and left.starts_on == left.ends_on == right.starts_on == right.ends_on
        and {left.cl_half, right.cl_half} == {"first", "second"}
    )
    return not same_day_halves
