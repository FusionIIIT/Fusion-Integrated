"""Leave request rules as pure functions — no Django, no DRF (BR-01..BR-05).

Everything a request can be refused for lives here, so the rules test in
milliseconds and the service layer only translates the refusal into HTTP.
"""
from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

HALF_DAY = Decimal("0.5")
MAX_SPAN_DAYS = 180
#: BR-04: a request may be recorded this many days after it started.
BACKDATE_LIMIT_DAYS = 7
HALF_DAY_PARTS = ("first", "second")


class RuleViolation(Exception):
    """Plain by design: services translate it, domain knows nothing of HTTP."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class LeaveTypeRules:
    """The subset of a leave type a pure function needs."""

    code: str
    name: str
    counts_calendar_days: bool
    allows_half_day: bool
    requires_reason: bool


@dataclass(frozen=True)
class LeaveRequest:
    start_date: date
    end_date: date
    is_half_day: bool = False
    half_day_part: str = ""
    reason: str = ""


def is_working_day(day: date, holidays: Collection[date]) -> bool:
    """Weekends and the configured holiday calendar are not leave days."""
    return day.weekday() < 5 and day not in holidays


def working_days(start: date, end: date, holidays: Collection[date]) -> int:
    count, day = 0, start
    while day <= end:
        if is_working_day(day, holidays):
            count += 1
        day += timedelta(days=1)
    return count


def count_days(request: LeaveRequest, rules: LeaveTypeRules,
               holidays: Collection[date]) -> Decimal:
    """The figure frozen onto the application at submission (BR-01)."""
    if request.is_half_day:
        return HALF_DAY
    if rules.counts_calendar_days:
        return Decimal((request.end_date - request.start_date).days + 1)
    return Decimal(working_days(request.start_date, request.end_date, holidays))


def validate_request(request: LeaveRequest, rules: LeaveTypeRules,
                     holidays: Collection[date], today: date) -> None:
    """Every submission rule in one place; the first failure is the answer."""
    if request.end_date < request.start_date:
        raise RuleViolation("dates_out_of_order",
                            "The end date cannot be before the start date.")
    if (request.end_date - request.start_date).days + 1 > MAX_SPAN_DAYS:
        raise RuleViolation("span_too_long",
                            f"A single request may not exceed {MAX_SPAN_DAYS} days;"
                            " split it into shorter ones.")
    if request.start_date < today - timedelta(days=BACKDATE_LIMIT_DAYS):
        raise RuleViolation("too_far_back",
                            "Leave can be recorded at most"
                            f" {BACKDATE_LIMIT_DAYS} days after it started;"
                            " contact the leave administrator about older gaps.")

    if request.is_half_day:
        if request.start_date != request.end_date:
            raise RuleViolation("half_day_multiple_days",
                                "A half day can only be taken on a single day.")
        if request.half_day_part not in HALF_DAY_PARTS:
            raise RuleViolation("half_day_part_required",
                                "Say which half of the day the leave covers.")
        if not rules.allows_half_day:
            raise RuleViolation("half_day_not_allowed",
                                f"{rules.name} does not allow half days.")

    if rules.requires_reason and not request.reason.strip():
        raise RuleViolation("reason_required",
                            f"{rules.name} needs a reason on the application.")

    if not request.is_half_day and count_days(request, rules, holidays) < 1:
        raise RuleViolation("no_working_days",
                            "That range covers no working days — weekends and"
                            " holidays are not counted.")
    if request.is_half_day and not is_working_day(request.start_date, holidays):
        raise RuleViolation("no_working_days",
                            "That day is a weekend or a holiday, not a working day.")
