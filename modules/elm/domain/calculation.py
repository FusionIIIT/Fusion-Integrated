"""How many leave days a request costs, and whether two requests collide."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from modules.elm.domain import leave_types as lt
from modules.elm.domain.errors import RuleViolation

MAX_SPAN_DAYS = 366
HALF_DAY = Decimal("0.5")


def is_weekend(day: date) -> bool:
    return day.weekday() >= 5


def leave_days(leave_type: str, start: date, end: date, half_day: str,
               closed_days: Iterable[date] = ()) -> Decimal:
    """Days charged to the balance (BR-EL-010, BR-EL-011)."""
    if end < start:
        raise RuleViolation("The end date must not be before the start date.", "BR-EL-012")
    span = (end - start).days + 1
    if span > MAX_SPAN_DAYS:
        raise RuleViolation("A single request cannot span more than a year.", "BR-EL-012")
    closed = frozenset(closed_days)

    if half_day != lt.NO_HALF:
        if leave_type not in lt.HALF_DAY_TYPES:
            raise RuleViolation("Only CL can be taken for half a day.", "BR-EL-010")
        if half_day not in lt.HALVES or start != end:
            raise RuleViolation("A half-day request covers one date and one half.", "BR-EL-010")
        if is_weekend(start) or start in closed:
            raise RuleViolation("A half day must fall on a working day.", "BR-EL-010")
        return HALF_DAY

    if leave_type == lt.RH:
        if start != end:
            raise RuleViolation("A restricted holiday is a single day.", "BR-EL-003")
        return Decimal(1)

    if leave_type in lt.CONTINUOUS_COUNT:
        return Decimal(span)

    counted = sum(
        1 for offset in range(span)
        if not is_weekend(start + timedelta(days=offset))
        and (start + timedelta(days=offset)) not in closed)
    if counted == 0:
        raise RuleViolation("The period contains no working day.", "BR-EL-011")
    return Decimal(counted)


@dataclass(frozen=True)
class Period:
    start: date
    end: date
    half: str = lt.NO_HALF

    @property
    def is_half(self) -> bool:
        return self.half != lt.NO_HALF


def overlaps(a: Period, b: Period) -> bool:
    """BR-EL-012. Two half-day requests on one date clash only in the same half."""
    if a.end < b.start or b.end < a.start:
        return False
    if a.is_half and b.is_half and a.start == b.start:
        return a.half == b.half
    return True


def find_overlap(new: Period, existing: Iterable[Period]) -> Period | None:
    return next((p for p in existing if overlaps(new, p)), None)
