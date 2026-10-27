"""Pure ELM leave-day and entitlement rules (Lab 6 pilot scope)."""

from datetime import date, timedelta
from decimal import Decimal

SUPPORTED = ("CL", "RH", "SCL", "EL", "COL", "VL")
DEFAULT_ENTITLEMENTS = {"CL": 8, "RH": 2, "SCL": 15, "EL": 30, "COL": 20, "VL": 60}
CONTINUOUS = frozenset({"EL", "COL", "VL"})


def eligible(category: str, employee_kind: str) -> bool:
    if category not in SUPPORTED or employee_kind not in ("faculty", "staff"):
        return False
    return category != "VL" or employee_kind == "faculty"


def count_days(
    category: str,
    start: date,
    end: date,
    half_day: str = "NONE",
    closed_days: frozenset[date] = frozenset(),
) -> Decimal:
    if category not in SUPPORTED:
        raise ValueError("Unsupported leave category.")
    if end < start:
        raise ValueError("The leave end date must not precede its start date.")
    if half_day not in ("NONE", "FIRST", "SECOND"):
        raise ValueError("Invalid half-day selection.")
    if half_day != "NONE":
        if category != "CL" or start != end:
            raise ValueError("Half-day leave is supported only for one-day CL.")
        if start.weekday() >= 5 or start in closed_days:
            raise ValueError("CL must fall on a working day.")
        return Decimal("0.5")
    total = Decimal("0")
    day = start
    while day <= end:
        if category in CONTINUOUS or (day.weekday() < 5 and day not in closed_days):
            total += 1
        day += timedelta(days=1)
    if not total:
        raise ValueError("Leave interval has no applicable leave days.")
    return total


def overlaps(
    existing_start: date,
    existing_end: date,
    new_start: date,
    new_end: date,
    existing_half: str = "NONE",
    new_half: str = "NONE",
) -> bool:
    if existing_end < new_start or new_end < existing_start:
        return False
    return not (
        existing_start == existing_end == new_start == new_end
        and {existing_half, new_half} == {"FIRST", "SECOND"}
    )


def remaining(allotted: Decimal, used: Decimal, requested: Decimal) -> Decimal:
    values = (allotted, used, requested)
    if any(not value.is_finite() for value in values):
        raise ValueError("Leave amounts must be finite numbers.")
    if allotted < 0 or used < 0 or requested <= 0:
        raise ValueError("Invalid leave amount.")
    available = allotted - used
    if requested > available:
        raise ValueError("Insufficient remaining leave balance.")
    return available - requested
