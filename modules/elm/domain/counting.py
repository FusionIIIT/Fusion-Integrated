"""Leave-day counting calculations (BR-EL-010, BR-EL-011)."""

import datetime
from collections.abc import Container
from decimal import Decimal


def calculate_chargeable_days(
    category: str,
    start_date: datetime.date,
    end_date: datetime.date,
    half_day: bool = False,
    closed_holidays: Container[datetime.date] | None = None,
) -> Decimal:
    """Calculate chargeable days according to category-specific rules.

    BR-EL-010: Half-day CL consumes 0.5 CL day.
    BR-EL-011: For EL, COL, and VL, intervening weekends and closed holidays
    within the continuous interval count as leave days. For CL, SCL, and RH,
    weekends and closed holidays do not count.
    """
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")

    # Half day applies only to single-day CL (BR-EL-010)
    if half_day:
        if category == "CL" and start_date == end_date:
            return Decimal("0.5")
        raise ValueError("Half-day leave is only applicable to single-day Casual Leave.")

    # Continuous counting categories (BR-EL-011)
    if category in ("EL", "COL", "VL"):
        total_days = (end_date - start_date).days + 1
        return Decimal(str(total_days))

    # Working day counting for CL, SCL, RH
    closed_set = closed_holidays or set()
    chargeable = 0
    cur = start_date
    one_day = datetime.timedelta(days=1)

    while cur <= end_date:
        # Weekend check (5 = Saturday, 6 = Sunday)
        is_weekend = cur.weekday() in (5, 6)
        is_holiday = cur in closed_set

        if not is_weekend and not is_holiday:
            chargeable += 1

        cur += one_day

    return Decimal(str(chargeable))
