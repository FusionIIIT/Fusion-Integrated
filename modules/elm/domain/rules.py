"""Pure ELM policy rules; no Django or HTTP dependencies."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

LEAVE_TYPES = ("CL", "RH", "SCL", "EL", "COL", "VL")
CONTINUOUS_TYPES = frozenset({"EL", "COL", "VL"})


def count_leave_days(start: date, end: date, category: str, *,
                     holidays: set[date] | None = None,
                     half_day: bool = False) -> Decimal:
    if end < start:
        raise ValueError("The end date must be on or after the start date.")
    if category not in LEAVE_TYPES:
        raise ValueError("Unsupported leave category.")
    if half_day and (category != "CL" or start != end):
        raise ValueError("Only a single-day CL request can be a half day.")
    if half_day:
        return Decimal("0.5")
    if category in CONTINUOUS_TYPES:
        return Decimal((end - start).days + 1)
    holidays = holidays or set()
    days = 0
    current = start
    while current <= end:
        if current.weekday() < 5 and current not in holidays:
            days += 1
        current += timedelta(days=1)
    return Decimal(days)


def annual_entitlement(category: str, employee_kind: str) -> Decimal:
    if category not in LEAVE_TYPES:
        raise ValueError("Unsupported leave category.")
    if category == "EL":
        return Decimal("0") if employee_kind == "faculty" else Decimal("30")
    if category == "VL":
        return Decimal("60") if employee_kind == "faculty" else Decimal("0")
    return {
        "CL": Decimal("8"),
        "RH": Decimal("2"),
        "SCL": Decimal("15"),
        "COL": Decimal("20"),
    }[category]


def overlaps(start: date, end: date, other_start: date, other_end: date, *,
             half_day_part: str | None = None,
             other_half_day_part: str | None = None,
             category: str = "") -> bool:
    if end < other_start or other_end < start:
        return False
    return not (
        category == "CL" and start == end == other_start == other_end
        and half_day_part and other_half_day_part
        and half_day_part != other_half_day_part
    )


def year_end_credit(category: str, balance: Decimal) -> tuple[Decimal, Decimal]:
    """Return (same-category carry-forward, EL credit from VL conversion)."""
    if category == "EL" or category == "COL":
        return max(balance, Decimal("0")), Decimal("0")
    if category == "VL":
        return Decimal("0"), max(balance, Decimal("0")) / Decimal("2")
    return Decimal("0"), Decimal("0")
