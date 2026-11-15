"""Chargeable days and calendar checks (BR-EL-003, 006, 010, 011, 031)."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from modules.elm.domain import categories as c

HALF = Decimal("0.5")


class InvalidPeriod(Exception):
    pass


@dataclass(frozen=True)
class Calendar:
    closed_holidays: frozenset[date] = frozenset()
    restricted_holidays: frozenset[date] = frozenset()
    vacations: tuple[tuple[date, date], ...] = field(default_factory=tuple)


def _days(start: date, end: date) -> Iterable[date]:
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def is_working_day(d: date, cal: Calendar) -> bool:
    return d.weekday() < 5 and d not in cal.closed_holidays


def validate_period(category: str, start: date, end: date, half: str | None) -> None:
    if end < start:
        raise InvalidPeriod("The leave cannot end before it starts.")
    if half:
        if category != c.CL:
            raise InvalidPeriod("Only Casual Leave can be taken as a half day.")
        if half not in c.HALVES:
            raise InvalidPeriod("A half day must be the first or second half.")
        if start != end:
            raise InvalidPeriod("A half-day leave must start and end on the same date.")


def validate_rh_dates(start: date, end: date, cal: Calendar) -> None:
    for d in _days(start, end):
        if d not in cal.restricted_holidays:
            raise InvalidPeriod(
                f"{d.isoformat()} is not a Restricted Holiday in the published calendar.")


def validate_vacation(start: date, end: date, cal: Calendar) -> None:
    if not any(vs <= start and end <= ve for vs, ve in cal.vacations):
        raise InvalidPeriod(
            "Vacation Leave can only be taken inside a published vacation period.")


def chargeable_days(category: str, start: date, end: date, half: str | None,
                    cal: Calendar) -> Decimal:
    validate_period(category, start, end, half)
    if half:
        if not is_working_day(start, cal):
            raise InvalidPeriod("A half-day leave must fall on a working day.")
        return HALF
    if category in c.CONTINUOUS:
        return Decimal((end - start).days + 1)
    if category == c.RH:
        return Decimal(sum(1 for _ in _days(start, end)))
    n = sum(1 for d in _days(start, end) if is_working_day(d, cal))
    if n == 0:
        raise InvalidPeriod("The requested period contains no working days.")
    return Decimal(n)
