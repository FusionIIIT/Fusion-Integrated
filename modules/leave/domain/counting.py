"""Chargeable-day arithmetic (SRS-EL-008, SRS-EL-011/012, BR-EL-010, BR-EL-011)."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from modules.leave.domain.categories import CL, CONTINUOUS_COUNT, HALVES, RH, SCL

HALF_DAY = Decimal("0.5")


def _daterange(start: date, end: date):
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def chargeable_days(*, category: str, start: date, end: date,
                    half: str | None, closed_holidays: frozenset[date]
                    ) -> Decimal:
    """How many days this interval consumes from the leave account.

    BR-EL-010: first/second half CL consumes 0.5.
    BR-EL-011: EL/COL/VL count intervening weekends and closed holidays.
    SRS-EL-032: that continuous-day rule does not apply to CL, SCL or RH.
    """
    if end < start:
        raise ValueError("Leave end date precedes start date.")

    if category == CL and half in HALVES:
        if start != end:
            raise ValueError("Half-day CL must occupy a single date.")
        return HALF_DAY

    if category in CONTINUOUS_COUNT:
        return Decimal((end - start).days + 1)

    # CL (full day), SCL, RH: count dates that are not weekends or closed holidays.
    n = 0
    for d in _daterange(start, end):
        if d.weekday() >= 5:
            continue
        if d in closed_holidays:
            continue
        n += 1
    if category in (CL, SCL, RH) and n == 0:
        raise ValueError("Requested interval contains no chargeable day.")
    return Decimal(n)
