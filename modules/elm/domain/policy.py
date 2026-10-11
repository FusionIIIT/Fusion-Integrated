"""Leave categories, entitlement, day counting and overlap (BR-EL-001..014).

Pure Python: the service layer supplies calendars and balances, this module
only decides.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

CL, RH, SCL, EL, COL, VL = "CL", "RH", "SCL", "EL", "COL", "VL"
CATEGORIES = (CL, RH, SCL, EL, COL, VL)

#: BR-EL-016 / BR-EL-017: who gives the final word.
UNIT_HEAD_FINAL = frozenset({CL, RH})
HIGHER_SANCTION = frozenset({SCL, EL, COL, VL})
#: BR-EL-011: weekends and closed holidays inside the interval count.
CONTINUOUS = frozenset({EL, COL, VL})
#: BR-EL-025 / BR-EL-027: extension and formal resumption apply only here.
EXTENDABLE = frozenset({EL, COL, VL})
#: BR-EL-002/003/004: lapse at year end; EL and COL carry forward.
LAPSING = frozenset({CL, RH, SCL})
CARRY_FORWARD = frozenset({EL, COL})

FIRST_HALF, SECOND_HALF = "first", "second"
HALVES = (FIRST_HALF, SECOND_HALF)

FACULTY, STAFF = "faculty", "staff"
EMPLOYEE_KINDS = frozenset({FACULTY, STAFF})

HALF = Decimal("0.5")


class PolicyViolation(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def credited_categories(kind: str) -> tuple[str, ...]:
    """BR-EL-005 / BR-EL-006: EL is credited to non-faculty, VL to faculty."""
    if kind == FACULTY:
        return (CL, RH, SCL, COL, VL)
    if kind == STAFF:
        return (CL, RH, SCL, EL, COL)
    return ()


def applicable_categories(kind: str) -> frozenset[str]:
    """Faculty may also avail EL created by VL conversion (BR-EL-008)."""
    if kind == FACULTY:
        return frozenset({CL, RH, SCL, EL, COL, VL})
    if kind == STAFF:
        return frozenset({CL, RH, SCL, EL, COL})
    return frozenset()


def check_category(category: str, kind: str) -> None:
    """BR-EL-001."""
    if category not in CATEGORIES:
        raise PolicyViolation("unknown_category",
                              f"{category} is not a supported leave category.")
    if kind not in EMPLOYEE_KINDS:
        raise PolicyViolation("not_employee",
                              "Only faculty and staff can apply for leave.")
    if category not in applicable_categories(kind):
        raise PolicyViolation("category_not_applicable",
                              f"{category} is not applicable to {kind}.")


def check_period(category: str, start: date, end: date, half: str | None) -> None:
    if end < start:
        raise PolicyViolation("bad_period", "The end date is before the start date.")
    if half is not None:
        if half not in HALVES:
            raise PolicyViolation("bad_half", "Choose the first or second half.")
        if category != CL:
            raise PolicyViolation("half_not_cl", "Only CL can be taken as a half day.")
        if start != end:
            raise PolicyViolation("half_one_day", "A half-day CL covers one date only.")


def _dates(start: date, end: date) -> Iterable[date]:
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def count_days(category: str, start: date, end: date, half: str | None,
               closed_holidays: set[date]) -> Decimal:
    """BR-EL-010 and BR-EL-011."""
    if half is not None:
        return HALF
    if category in CONTINUOUS:
        return Decimal((end - start).days + 1)
    working = sum(1 for d in _dates(start, end)
                  if d.weekday() < 5 and d not in closed_holidays)
    return Decimal(working)


def check_counted(days: Decimal) -> None:
    if days <= 0:
        raise PolicyViolation("no_working_days",
                              "The period has no working day to take leave on.")


def check_restricted_holidays(start: date, end: date,
                              restricted: set[date]) -> None:
    """BR-EL-003: every RH date must be a published Restricted Holiday."""
    missing = [d for d in _dates(start, end) if d not in restricted]
    if missing:
        raise PolicyViolation(
            "not_restricted_holiday",
            f"{missing[0].isoformat()} is not a Restricted Holiday in the "
            "published calendar.")


def check_vacation(start: date, end: date,
                   periods: Iterable[tuple[date, date]]) -> None:
    """BR-EL-006: VL only inside one Academic Calendar vacation period."""
    if not any(p_start <= start and end <= p_end for p_start, p_end in periods):
        raise PolicyViolation("outside_vacation",
                              "VL can be taken only inside a vacation period.")


def check_balance(requested: Decimal, available: Decimal) -> None:
    if requested > available:
        raise PolicyViolation(
            "insufficient_balance",
            f"You asked for {requested} days but only {available} are available.")


@dataclass(frozen=True)
class Interval:
    start: date
    end: date
    half: str | None = None


def overlaps(a: Interval, b: Interval) -> bool:
    """BR-EL-012: different CL halves on the same date do not overlap."""
    if a.end < b.start or b.end < a.start:
        return False
    same_day_halves = (a.half and b.half and a.half != b.half
                       and a.start == a.end == b.start == b.end)
    return not same_day_halves


def vl_to_el(unused_vl: Decimal) -> Decimal:
    """BR-EL-007: 2 VL : 1 EL, fractions kept."""
    return unused_vl / 2


def resumption_adjustment(approved_end: date, actual: date) -> int:
    """BR-EL-028: positive is extra leave (late), negative is days returned."""
    return (actual - approved_end).days
