"""Calendar-aware leave counting. Calendar data is passed in to keep this pure."""
from datetime import date, timedelta
from decimal import Decimal

CONTINUOUS_CATEGORIES = {"EL", "COL", "VL"}
WORKING_DAY_CATEGORIES = {"CL", "RH", "SCL"}


def _dates(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def chargeable_days(category: str, start: date, end: date, *, half: str = "", closed_dates: set[date] | None = None) -> Decimal:
    if end < start:
        raise ValueError("End date must not be before start date.")
    closed_dates = closed_dates or set()
    if category == "CL" and half:
        if start != end or half not in {"first", "second"}:
            raise ValueError("Half-day CL must be one half of a single date.")
        if start.weekday() >= 5 or start in closed_dates:
            raise ValueError("Half-day CL must fall on a working day.")
        return Decimal("0.5")
    if category in CONTINUOUS_CATEGORIES:
        return Decimal((end - start).days + 1)
    if category not in WORKING_DAY_CATEGORIES:
        raise ValueError(f"Unsupported leave category: {category}")
    return Decimal(sum(1 for d in _dates(start, end) if d.weekday() < 5 and d not in closed_dates))


def validate_rh_dates(start: date, end: date, restricted_dates: set[date]) -> None:
    if start != end or start not in restricted_dates:
        raise ValueError("RH must be taken on an applicable Restricted Holiday in the current published calendar.")


def validate_vacation(start: date, end: date, vacation_periods: list[tuple[date, date]]) -> None:
    if not any(start >= first and end <= last for first, last in vacation_periods):
        raise ValueError("VL must fall entirely within a published institute vacation period.")
