"""Validation of a leave request before it may progress (EL-UC-001 M4).

Fail closed, the way placement's eligibility engine does: an unknown category,
a missing fact or an empty vacation-period list all refuse rather than assume.
The rules are the ones the baseline states outright — BR-EL-001..015 and
BR-EL-030/031 — and `services/` supplies the facts, so this stays pure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from modules.leave.domain import categories as cat
from modules.leave.domain.categories import Interval


@dataclass(frozen=True)
class Request:
    """Everything the rules need, and nothing they do not."""

    category_code: str
    employee_kind: str
    start: date
    end: date
    half: str | None = None
    #: Balance already computed by the account service.
    available: Decimal = Decimal(0)
    #: From the currently effective published calendar.
    closed_dates: frozenset[date] = frozenset()
    restricted_holidays: frozenset[date] = frozenset()
    #: Vacation periods projected from the Academic Calendar (EXT-01).
    vacation_periods: tuple[tuple[date, date], ...] = ()
    #: The applicant's own active pending or approved leave.
    existing: tuple[Interval, ...] = ()
    #: Responsibility coverage, when required.
    substitute_required: bool = False
    substitute_user_id: int | None = None
    applicant_user_id: int | None = None
    substitute_intervals: tuple[Interval, ...] = ()


@dataclass(frozen=True)
class Outcome:
    code: str
    message: str


@dataclass(frozen=True)
class Verdict:
    is_valid: bool
    days: Decimal
    outcomes: tuple[Outcome, ...] = field(default_factory=tuple)

    @property
    def reasons(self) -> tuple[str, ...]:
        return tuple(o.code for o in self.outcomes)


def _in_vacation(start: date, end: date,
                 periods: tuple[tuple[date, date], ...]) -> bool:
    return any(p_start <= start and end <= p_end for p_start, p_end in periods)


def validate(req: Request) -> Verdict:
    """Run every applicable rule. Stops at the first failure it finds for each
    concern, but reports all of them at once — an employee fixing a form should
    not have to submit it four times to learn four things."""
    out: list[Outcome] = []
    code = req.category_code

    if code not in cat.CATEGORIES:
        return Verdict(False, Decimal(0), (Outcome(
            "category_not_supported",
            f"{code or 'No category'} is not a leave category this module "
            f"supports. Choose one of: {', '.join(cat.CATEGORIES)}."),))
    c = cat.category(code)

    if req.employee_kind not in c.kinds:
        return Verdict(False, Decimal(0), (Outcome(
            "category_not_applicable",
            f"{c.label} is not available to {req.employee_kind} employees."),))

    if req.end < req.start:
        return Verdict(False, Decimal(0), (Outcome(
            "invalid_period", "The leave cannot end before it starts."),))

    if req.half:
        if not c.allows_half_day:
            return Verdict(False, Decimal(0), (Outcome(
                "half_day_not_allowed",
                f"{c.label} cannot be taken for half a day. "
                f"Per BR-EL-010, only CL supports half-day requests."),))
        if req.start != req.end:
            return Verdict(False, Decimal(0), (Outcome(
                "half_day_single_date",
                "A half-day request must be for a single date. "
                "Per BR-EL-010, CL first-half and second-half on the same date "
                "are not overlapping when they occupy different halves."),))

    days = cat.leave_days(code=code, start=req.start, end=req.end,
                          half=req.half, closed_dates=req.closed_dates)

    if not c.continuous_counting and days <= 0:
        out.append(Outcome(
            "no_duty_days",
            "Every day in that period is a weekend or a closed holiday, so "
            "there is nothing to sanction."))

    # BR-EL-011: EL/COL/VL count continuously (weekends/holidays count as leave days),
    #           CL/SCL/RH count only duty days (weekends/holidays do not count).
    if days > req.available:
        out.append(Outcome(
            "insufficient_balance",
            f"{c.label} balance is {req.available} day(s); this request needs "
            f"{days}."))

    # BR-EL-003: RH must name a Restricted Holiday from the effective calendar.
    if code == cat.RH and req.start not in req.restricted_holidays:
        out.append(Outcome(
            "rh_not_in_calendar",
            "That date is not a Restricted Holiday in the currently published "
            "calendar."))

    # BR-EL-006: VL only inside a vacation period.
    if c.requires_vacation_period and not _in_vacation(req.start, req.end,
                                                      req.vacation_periods):
        out.append(Outcome(
            "outside_vacation_period",
            "Vacation Leave may be availed only inside a vacation period from "
            "the Academic Calendar."))

    # BR-EL-012: no overlap with the applicant's own active leave.
    mine = Interval(req.start, req.end, req.half)
    if any(mine.overlaps(other) for other in req.existing):
        out.append(Outcome(
            "overlapping_leave",
            "You already have pending or approved leave on one of those days."))

    # BR-EL-013: Station Leave rides along on the same application; there is
    # nothing separate to validate, only to remember not to invent.

    return Verdict(not out, days, tuple(out))
