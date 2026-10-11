"""Leave entitlement policies (BR-EL-002–009)."""

from datetime import date, timedelta
from decimal import Decimal
from enum import Enum


class LeaveCategory(str, Enum):
    CL = "CL"
    RH = "RH"
    SCL = "SCL"
    EL = "EL"
    COL = "COL"
    VL = "VL"


def annual_entitlement(
    category: str, *, faculty: bool, eligible: bool = True
) -> Decimal:
    if category == "CL":
        return Decimal(8)
    if category == "RH":
        return Decimal(2)
    if category == "SCL":
        return Decimal(15)
    if category == "EL":
        return Decimal(30) if not faculty else Decimal(0)
    if category == "COL":
        return Decimal(20) if eligible else Decimal(0)
    if category == "VL":
        return Decimal(60) if faculty else Decimal(0)
    raise ValueError("Unknown category")


def inclusive_days(start: date, end: date) -> int:
    if end < start:
        raise ValueError("End date must not be before start date")
    if start == end:
        return 1
    return (end - start).days + 1


def chargeable_day_count(
    category: str,
    start: date,
    end: date,
    *,
    closed_dates: set[date] | frozenset[date] = frozenset(),
    restricted_holidays: set[date] | frozenset[date] = frozenset(),
) -> Decimal:
    if end < start:
        raise ValueError("End date must not be before start date")
    if category in ("EL", "COL", "VL"):
        return Decimal(inclusive_days(start, end))
    if category == "RH":
        if start != end or start not in restricted_holidays:
            raise ValueError("RH must match a published restricted holiday")
        return Decimal(1)
    if category in ("CL", "SCL"):
        count = 0
        for offset in range(inclusive_days(start, end)):
            day = start + timedelta(days=offset)
            if day.weekday() < 5 and day not in closed_dates:
                count += 1
        return Decimal(count)
    raise ValueError("Unknown leave category")


def chargeable_request_days(
    category: str,
    start: date,
    end: date,
    *,
    half_day: str | None = None,
    closed_dates: set[date] | frozenset[date] = frozenset(),
    restricted_holidays: set[date] | frozenset[date] = frozenset(),
) -> Decimal:
    if half_day is None:
        return chargeable_day_count(
            category,
            start,
            end,
            closed_dates=closed_dates,
            restricted_holidays=restricted_holidays,
        )
    if category != "CL" or start != end or half_day not in {"first_half", "second_half"}:
        raise ValueError("Half-day leave must be one CL date and name its half")
    return Decimal("0.5")


def overlaps(
    first_category: str,
    first_start: date,
    first_end: date,
    first_half: str | None,
    second_category: str,
    second_start: date,
    second_end: date,
    second_half: str | None,
) -> bool:
    if first_end < first_start or second_end < second_start:
        raise ValueError("End date must not be before start date")
    if first_end < second_start or second_end < first_start:
        return False
    same_single_day = first_start == first_end == second_start == second_end
    if (
        first_category == second_category == "CL"
        and same_single_day
        and first_half is not None
        and second_half is not None
        and first_half != second_half
    ):
        return False
    return True


def convert_vl_to_el(unused_vl: Decimal) -> Decimal:
    if unused_vl < Decimal(0):
        raise ValueError("Negative input is not allowed")
    return unused_vl / Decimal(2)
