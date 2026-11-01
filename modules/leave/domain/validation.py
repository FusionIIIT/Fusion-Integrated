"""Request validation before anything is allowed to progress (BR-EL-001..013).

The order is deliberate, not incidental: the refusal that tells the employee
what to fix goes before the one that only says no (BR-EL-001 first, balance
last).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from modules.leave.domain import categories as cat
from modules.leave.domain import counting
from modules.leave.domain.errors import RuleViolation


@dataclass(frozen=True)
class Interval:
    start: date
    end: date
    half: str = ""
    category: str = ""
    reference: str = "pending"


@dataclass(frozen=True)
class RequestFacts:
    user_id: int
    category: str
    start: date
    end: date
    half: str = ""
    is_faculty: bool = False
    balance: Decimal = Decimal("0")
    committed: Decimal = Decimal("0")
    active_intervals: tuple[Interval, ...] = field(default_factory=tuple)
    closed_dates: frozenset[date] = frozenset()
    restricted_holiday_dates: frozenset[date] = frozenset()
    vacation_periods: tuple[tuple[date, date], ...] = field(default_factory=tuple)
    today: date | None = None
    max_backdate_days: int = 0
    #: The ongoing approved leave an extension hangs off, when this is one.
    extension_of: tuple[date, date] | None = None


def days_required(facts: RequestFacts) -> Decimal:
    """Validate, and answer how many days the request consumes."""
    _category(facts)
    _period(facts)
    _category_calendar(facts)
    days = _counting(facts)
    _overlap(facts)
    # RH balance is checked after calendar applicability, but only if RH passes
    # the calendar check (BR-EL-003: RH must be a published restricted holiday).
    _balance(facts, days)
    return days


def _category(facts: RequestFacts) -> None:
    if not cat.is_known(facts.category):
        raise RuleViolation(
            f"'{facts.category}' is not one of CL, RH, SCL, EL, COL or VL.",
            code="unknown_category")
    if not cat.applicable_to(facts.category, is_faculty=facts.is_faculty):
        raise RuleViolation(
            f"{cat.LABELS[facts.category]} is available to faculty members only.",
            code="category_not_applicable")


def _period(facts: RequestFacts) -> None:
    if facts.end < facts.start:
        raise RuleViolation("The leave end date is before its start date.",
                            code="period_invalid")
    today = facts.today or date.today()
    earliest = today.fromordinal(today.toordinal() - max(0, facts.max_backdate_days))
    if facts.start < earliest:
        raise RuleViolation(
            f"Leave cannot be applied for from before {earliest.isoformat()}.",
            code="period_in_past")


def _category_calendar(facts: RequestFacts) -> None:
    days = counting.dates_between(facts.start, facts.end)
    if facts.category == cat.RH:
        applicable = [d for d in days if d in facts.restricted_holiday_dates]
        if not applicable:
            raise RuleViolation(
                "A Restricted Holiday may be taken only on a date published as a "
                "restricted holiday.",
                code="rh_not_published")
    if facts.category == cat.VL and not _inside_vacation(facts):
        raise RuleViolation(
            "Vacation Leave may be availed only during a vacation period of the "
            "institute Academic Calendar.",
            code="vl_outside_vacation")


def _inside_vacation(facts: RequestFacts) -> bool:
    if not facts.vacation_periods:
        raise RuleViolation(
            "No vacation period is configured, so Vacation Leave cannot be "
            "validated. Ask an administrator to publish the academic vacation dates.",
            code="vacation_calendar_missing")
    return any(start <= facts.start and facts.end <= end
               for start, end in facts.vacation_periods)


def _counting(facts: RequestFacts) -> Decimal:
    if facts.category == cat.RH:
        # BR-EL-003: RH is taken only on published restricted holidays.
        # Count only the requested dates that are actual restricted holidays.
        days = counting.dates_between(facts.start, facts.end)
        rh_days = [d for d in days if d in facts.restricted_holiday_dates]
        days = Decimal(len(rh_days))
    else:
        days = counting.count_days(category=facts.category, start=facts.start,
                                   end=facts.end, half=facts.half,
                                   closed_dates=facts.closed_dates)
    if days <= 0:
        raise RuleViolation(
            "The requested dates fall on weekends and closed holidays only, so the "
            "request would consume no leave day.",
            code="no_leave_days")
    return days


def _overlap(facts: RequestFacts) -> None:
    """BR-EL-012, with the single CL half-day exception."""
    for other in facts.active_intervals:
        if other.end < facts.start or other.start > facts.end:
            continue
        if counting.same_date_different_halves(
            category=facts.category, half=facts.half, start=facts.start, end=facts.end,
            other_category=other.category, other_half=other.half,
            other_start=other.start, other_end=other.end,
        ):
            continue
        raise RuleViolation(
            f"This overlaps your {other.reference} leave from "
            f"{other.start.isoformat()} to {other.end.isoformat()}.",
            code="overlapping_leave")


def _balance(facts: RequestFacts, days: Decimal) -> None:
    left = facts.balance - facts.committed
    if days > left:
        raise RuleViolation(
            f"{days} day(s) requested but only {left} are available for "
            f"{cat.LABELS[facts.category]}.",
            code="insufficient_balance")
