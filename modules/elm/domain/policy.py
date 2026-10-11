"""ELM leave-day arithmetic and eligibility maths.

Pure functions over dates and decimals — no Django, no database.
The counting rules are PS §4:

* EL, COL and VL count **continuously**: every calendar day inside
  the approved interval is a leave day, weekends and closed
  holidays included.
* CL, SCL and RH do **not** count continuously: intervening
  weekends and closed holidays inside the interval are not leave
  days.

Half days exist only for CL (PS §3): first/second half of a day
consumes ``0.5`` CL days.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from modules.elm.domain.leave_types import (
    CL,
    CONTINUOUS_COUNTING_CATEGORIES,
    HALF_FIRST,
    HALF_FULL,
    HALF_SECOND,
)

DAY = Decimal("1")
HALF = Decimal("0.5")
ZERO = Decimal("0")

BOTH_HALVES = frozenset({HALF_FIRST, HALF_SECOND})


@dataclass(frozen=True)
class LeaveInterval:
    """A requested (or approved) leave interval with its half-day flags."""

    category: str
    start: date
    end: date
    start_half: str = HALF_FULL
    end_half: str = HALF_FULL

    def halves(self) -> tuple[str, str]:
        return (
            self.start_half or HALF_FULL,
            self.end_half or HALF_FULL,
        )


def span_days(start: date, end: date, *, closed: frozenset[date]) -> list[date]:
    """The calendar days inside ``[start, end]`` that count as leave
    days for a non-continuous category: weekdays that are not closed
    holidays. Continuous categories take every calendar day instead
    (see :func:`count_days`)."""
    if end < start:
        return []
    days: list[date] = []
    current = start
    while current <= end:
        if current.weekday() < 5 and current not in closed:
            days.append(current)
        current += timedelta(days=1)
    return days


def _single_day_halves(start_half: str, end_half: str) -> frozenset[str]:
    """Which halves of a single-day request are on leave."""
    if start_half == HALF_FULL and end_half == HALF_FULL:
        return BOTH_HALVES
    if start_half == HALF_FULL:
        return frozenset({end_half})
    if end_half == HALF_FULL:
        return frozenset({start_half})
    # first + second half of the same day is a full day.
    return BOTH_HALVES


def count_days(interval: LeaveInterval,
               *,
               closed: frozenset[date] = frozenset(),
               restricted_holidays: frozenset[date] = frozenset(),
               ) -> Decimal:
    """Leave days consumed by ``interval``.

    ``closed`` is the set of closed-holiday dates in the effective
    published calendar; it only matters for non-continuous
    categories, where closed days never count as leave. A
    restricted-holiday date is not institute-closed — the employee
    may take it as RH — so RH dates are excluded from ``closed``.
    """
    closed = frozenset(closed) - frozenset(restricted_holidays)
    if interval.end < interval.start:
        return ZERO
    if interval.category in CONTINUOUS_COUNTING_CATEGORIES:
        days = []
        current = interval.start
        while current <= interval.end:
            days.append(current)
            current += timedelta(days=1)
    else:
        days = span_days(interval.start, interval.end, closed=closed)
    if not days:
        return ZERO
    total = Decimal(len(days))
    start_half, end_half = interval.halves()
    if len(days) == 1:
        return DAY if _single_day_halves(start_half, end_half) == BOTH_HALVES else HALF
    if start_half in (HALF_FIRST, HALF_SECOND):
        total -= HALF
    if end_half in (HALF_FIRST, HALF_SECOND):
        total -= HALF
    return total


def _boundary_halves(interval: LeaveInterval, first: bool) -> frozenset[str]:
    """Halves occupied on the interval's first (or last) day."""
    half = interval.start_half if first else interval.end_half
    half = half or HALF_FULL
    return BOTH_HALVES if half == HALF_FULL else frozenset({half})


def intervals_overlap(a: LeaveInterval, b: LeaveInterval) -> bool:
    """True when two intervals collide.

    Carries the CL half-day exception (BR-EL-013): two CL requests
    on the *same single date* do not overlap when one covers only
    the first half and the other only the second half.
    """
    if a.start > b.end or b.start > a.end:
        return False
    if (a.category == CL and b.category == CL
            and a.start == a.end and b.start == b.end
            and a.start == b.start):
        a_halves = _single_day_halves(a.start_half, a.end_half)
        b_halves = _single_day_halves(b.start_half, b.end_half)
        return not a_halves.isdisjoint(b_halves)
    return True


def overlaps_any(candidate: LeaveInterval,
                 existing: Iterable[LeaveInterval]) -> LeaveInterval | None:
    """The first existing interval that collides with ``candidate``,
    or ``None`` when the candidate is clear."""
    for other in existing:
        if intervals_overlap(candidate, other):
            return other
    return None


# -- balance and entitlement maths ------------------------------------------

def available_balance(opening: Decimal, entitled: Decimal,
                      used: Decimal, pending: Decimal) -> Decimal:
    """Days an employee may still apply for (BR-EL-001/005).

    Pending (non-terminal) requests reserve their days so a person
    cannot double-book the same balance with two in-flight requests.
    """
    return opening + entitled - used - pending


def vl_to_el_conversion(unused_vl: Decimal,
                        ratio: Decimal = Decimal("2")) -> Decimal:
    """Year-end faculty VL -> EL credit (PS §3, BR-EL-007).

    Two vacation days convert to one earned leave day, with the
    fractional part preserved — 61 unused VL days credit 30.5 EL.
    """
    if unused_vl <= ZERO:
        return ZERO
    return (unused_vl / ratio).quantize(Decimal("0.01"))


def year_end_outcome(category: str, employee_kind: str,
                     unused: Decimal) -> str:
    """What happens to unused days of ``category`` at the leave-year
    boundary (PS §3): ``lapse``, ``convert`` or ``carry_forward``."""
    if category in (CL, "RH", "SCL"):
        return "lapse"
    if category == "VL":
        return "convert" if employee_kind == "faculty" else "lapse"
    return "carry_forward"  # EL, COL
