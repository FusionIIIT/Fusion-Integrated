from datetime import date, timedelta
from decimal import Decimal

ENTITLEMENTS = {"CL": Decimal("8"), "RH": Decimal("2"), "SCL": Decimal("15"),
                "EL": Decimal("30"), "VL": Decimal("60"), "COL": Decimal("20")}


def count_leave_days(category: str, start: date, end: date, half_day: str | None = None,
                     closed_dates: set[date] | None = None) -> Decimal:
    if category not in ENTITLEMENTS or end < start:
        raise ValueError("Invalid leave category or interval")
    if category == "CL" and half_day in {"first", "second"}:
        if start != end:
            raise ValueError("Half-day CL must be one date")
        return Decimal("0.5")
    if category in {"EL", "COL", "VL"}:
        return Decimal((end - start).days + 1)
    closed_dates = closed_dates or set()
    total, current = 0, start
    while current <= end:
        if current not in closed_dates:
            total += 1
        current += timedelta(days=1)
    return Decimal(total)


def intervals_overlap(a_start: date, a_end: date, a_half: str | None,
                      b_start: date, b_end: date, b_half: str | None) -> bool:
    if a_end < b_start or b_end < a_start:
        return False
    return not (a_start == a_end == b_start == b_end
                and a_half in {"first", "second"} and b_half in {"first", "second"}
                and a_half != b_half)
