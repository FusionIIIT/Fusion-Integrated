"""How many leave days a requested period costs (BR-EL-011, BR-EL-010).

The category decides the counting boundary, and the boundary is the *only*
thing that differs between the two families:

    EL / COL / VL   continuous — every calendar day in the interval is charged,
                    intervening weekends and closed holidays included
    RH              one day per requested Restricted Holiday date, which is
                    itself a holiday, so nothing is skipped
    CL / SCL        working days only — a weekend or closed holiday inside the
                    interval is not charged

CL additionally supports a half day, which consumes 0.5 (BR-EL-010).

Pure Python: the caller passes the calendar data in.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from modules.leave.domain import categories as cat

#: Saturday and Sunday, as date.weekday() reports them.
WEEKEND = (5, 6)

#: Categories that charge every calendar day in the interval.
_COUNTS_EVERY_DAY = frozenset({cat.EL, cat.COL, cat.VL, cat.RH})


@dataclass(frozen=True)
class Chargeable:
    """The verdict for one requested period, with the reasoning kept."""

    days: Decimal
    charged: tuple[date, ...]
    skipped: tuple[date, ...]

    @property
    def is_half_day(self) -> bool:
        return self.days == cat.HALF_DAY_DAYS


def daterange(start: date, end: date) -> tuple[date, ...]:
    if end < start:
        return ()
    return tuple(start + timedelta(days=i) for i in range((end - start).days + 1))


def is_working_day(day: date, closed_holidays: Iterable[date] = ()) -> bool:
    """Not a weekend and not a closed holiday."""
    return day.weekday() not in WEEKEND and day not in set(closed_holidays)


def chargeable_days(*, category: str, start: date, end: date, half: str = "",
                    closed_holidays: Iterable[date] = ()) -> Chargeable:
    """Charge for `start..end` inclusive under the category's counting rule."""
    days = daterange(start, end)
    if not days:
        return Chargeable(Decimal("0"), (), ())

    if half:
        # A half day is one day at half weight; `half` is only ever set on a
        # single-date CL request, which the table constrains.
        return Chargeable(cat.HALF_DAY_DAYS, (days[0],), days[1:])

    holidays = set(closed_holidays)
    if category in _COUNTS_EVERY_DAY:
        return Chargeable(Decimal(len(days)), days, ())

    charged = tuple(d for d in days if is_working_day(d, holidays))
    skipped = tuple(d for d in days if d not in charged)
    return Chargeable(Decimal(len(charged)), charged, skipped)
