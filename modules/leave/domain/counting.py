"""How many days a leave interval charges against a balance."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum

from modules.leave.domain.categories import Category, counts_intervening_days

HALF = Decimal("0.5")
ONE = Decimal("1")


class Half(StrEnum):
    FIRST = "FIRST"
    SECOND = "SECOND"


class TailPolicy(StrEnum):
    """What happens to a non-working tail when leave is cut short."""

    #: Charge up to the last working day taken.
    TRIM_TO_LAST_WORKING_DAY = "TRIM_TO_LAST_WORKING_DAY"
    #: Charge every calendar day up to the resumption date.
    CHARGE_TO_RESUMPTION = "CHARGE_TO_RESUMPTION"


@dataclass(frozen=True)
class Calendar:
    """The closed days in force for a period. BR-EL-031."""

    holidays: frozenset[date]
    weekend_weekdays: frozenset[int] = frozenset({5, 6})

    def is_closed(self, day: date) -> bool:
        return day.weekday() in self.weekend_weekdays or day in self.holidays

    def is_working(self, day: date) -> bool:
        return not self.is_closed(day)


def days_in(start: date, end: date) -> Iterable[date]:
    if end < start:
        return
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)


def chargeable_days(
    category: Category,
    start: date,
    end: date,
    calendar: Calendar,
    *,
    half: Half | None = None,
) -> Decimal:
    """Days charged for an interval, before any early-resumption adjustment."""
    if end < start:
        raise ValueError("leave cannot end before it starts")
    if half is not None:
        if start != end:
            raise ValueError("a half day must be a single date")
        return HALF
    if counts_intervening_days(category):
        return Decimal(len(list(days_in(start, end))))
    return Decimal(sum(1 for d in days_in(start, end) if calendar.is_working(d)))


def actual_days_on_early_return(
    category: Category,
    start: date,
    approved_end: date,
    resumed_on: date,
    calendar: Calendar,
    policy: TailPolicy = TailPolicy.TRIM_TO_LAST_WORKING_DAY,
) -> Decimal:
    """Days actually charged when duty resumes before the approved end."""
    if resumed_on <= start:
        return Decimal(0)
    if resumed_on > approved_end:
        return chargeable_days(category, start, approved_end, calendar)

    last_day = resumed_on - timedelta(days=1)
    if counts_intervening_days(category) and policy is TailPolicy.TRIM_TO_LAST_WORKING_DAY:
        while last_day >= start and calendar.is_closed(last_day):
            last_day -= timedelta(days=1)
    if last_day < start:
        return Decimal(0)
    return chargeable_days(category, start, last_day, calendar)


def restored_days(
    category: Category,
    start: date,
    approved_end: date,
    resumed_on: date,
    calendar: Calendar,
    policy: TailPolicy = TailPolicy.TRIM_TO_LAST_WORKING_DAY,
) -> Decimal:
    """The unused portion returned to the balance on early resumption."""
    approved = chargeable_days(category, start, approved_end, calendar)
    actual = actual_days_on_early_return(
        category, start, approved_end, resumed_on, calendar, policy
    )
    return approved - actual
