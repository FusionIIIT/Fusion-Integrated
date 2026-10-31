from datetime import timedelta

from .constants import HALF_DAY_NONE, HALF_DAY_FIRST, HALF_DAY_SECOND


def calculate_chargeable_days(
    category,
    start_date,
    end_date,
    half_day_type=HALF_DAY_NONE,
    holidays=None,
    weekends=None,
):
    holidays = set(holidays or [])
    weekends = set(weekends or [])

    if category in ("el", "col", "vl"):
        return float((end_date - start_date).days + 1)

    if half_day_type in (HALF_DAY_FIRST, HALF_DAY_SECOND):
        return 0.5

    count = 0
    current = start_date
    while current <= end_date:
        is_weekend = current.weekday() >= 5 or current in weekends
        if not is_weekend and current not in holidays:
            count += 1
        current += timedelta(days=1)
    return float(count)


def convert_vl_to_el(unused_vl):
    return unused_vl / 2.0