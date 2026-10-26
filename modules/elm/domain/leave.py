"""Leave categories, date counting and overlap rules from the ELM baseline."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum


class Category(StrEnum):
    CL = "CL"
    RH = "RH"
    SCL = "SCL"
    EL = "EL"
    COL = "COL"
    VL = "VL"


class Stage(StrEnum):
    UNIT_HEAD = "unit_head"
    ESTABLISHMENT = "establishment"
    FINAL = "final"
    DIRECTOR_SELF = "director_self"


class LeaveRuleError(ValueError):
    """A request violates a published leave rule."""


CONTINUOUS_CATEGORIES = frozenset({Category.EL, Category.COL, Category.VL})
EMPLOYEE_KINDS = frozenset({"faculty", "staff"})
CATEGORY_LIMITS = {
    Category.CL: Decimal("8"), Category.RH: Decimal("2"),
    Category.SCL: Decimal("15"), Category.EL: Decimal("30"),
    Category.COL: Decimal("20"), Category.VL: Decimal("60"),
}


def employee_is_eligible(category: Category, employee_kind: str) -> bool:
    kind = employee_kind.casefold()
    if kind not in EMPLOYEE_KINDS:
        return False
    if category == Category.EL:
        return kind == "staff"
    if category == Category.VL:
        return kind == "faculty"
    return True


def chargeable_days(
    category: Category,
    start: date,
    end: date,
    *,
    closed_dates: set[date] | frozenset[date] = frozenset(),
    restricted_dates: set[date] | frozenset[date] = frozenset(),
    half_day: str = "",
) -> Decimal:
    return sum(yearly_charges(category, start, end, closed_dates=closed_dates,
                              restricted_dates=restricted_dates,
                              half_day=half_day).values(), Decimal())


def yearly_charges(
    category: Category,
    start: date,
    end: date,
    *,
    closed_dates: set[date] | frozenset[date] = frozenset(),
    restricted_dates: set[date] | frozenset[date] = frozenset(),
    half_day: str = "",
) -> dict[int, Decimal]:
    charges: dict[int, Decimal] = defaultdict(Decimal)
    if end < start:
        raise LeaveRuleError("End date must be on or after start date.")
    if category == Category.RH:
        if start != end or start not in restricted_dates or half_day:
            raise LeaveRuleError("RH must be one published Restricted Holiday.")
        return {start.year: Decimal("1")}
    if half_day and (category != Category.CL or start != end
                     or half_day not in {"first", "second"}):
        raise LeaveRuleError("Only a one-date CL request can select a half day.")
    day_charge = Decimal("0.5" if half_day else "1")
    cursor = start
    while True:
        year_end = min(end, date(cursor.year, 12, 31))
        duration = (year_end - cursor).days + 1
        if category in CONTINUOUS_CATEGORIES:
            charges[cursor.year] += day_charge * duration
        else:
            full_weeks, remainder = divmod(duration, 7)
            weekdays = full_weeks * 5 + sum(
                (cursor.weekday() + offset) % 7 < 5 for offset in range(remainder)
            )
            charges[cursor.year] += day_charge * weekdays
        if year_end == end:
            break
        cursor = year_end + timedelta(days=1)
    if category not in CONTINUOUS_CATEGORIES:
        for day in closed_dates:
            if start <= day <= end and day.weekday() < 5:
                charges[day.year] -= day_charge
    charges = {year: amount for year, amount in charges.items() if amount}
    if not charges:
        raise LeaveRuleError("The requested period contains no chargeable leave days.")
    return dict(charges)


def requests_overlap(
    *,
    start: date,
    end: date,
    category: Category,
    half_day: str,
    other_start: date,
    other_end: date,
    other_category: Category,
    other_half_day: str,
) -> bool:
    if start > other_end or other_start > end:
        return False
    if (start == end == other_start == other_end
            and category == other_category == Category.CL
            and half_day and other_half_day and half_day != other_half_day):
        return False
    return True


def validate_route(category: Category, stages: list[str], *, director: bool = False) -> None:
    if director:
        if stages != [Stage.DIRECTOR_SELF]:
            raise LeaveRuleError("Director leave must use the configured self-sanction step.")
        return
    if category in {Category.CL, Category.RH}:
        if stages != [Stage.UNIT_HEAD]:
            raise LeaveRuleError("CL and RH use the Unit Head as final authority.")
        return
    allowed = {Stage.UNIT_HEAD, Stage.ESTABLISHMENT, Stage.FINAL}
    if (not stages or stages[0] != Stage.UNIT_HEAD or stages[-1] != Stage.FINAL
            or any(stage not in allowed for stage in stages)
            or stages.count(Stage.UNIT_HEAD) != 1
            or stages.count(Stage.FINAL) != 1
            or stages.count(Stage.ESTABLISHMENT) > 1):
        raise LeaveRuleError(
            "Higher-sanction leave needs Unit Head review, an optional Establishment step, and final sanction."
        )
