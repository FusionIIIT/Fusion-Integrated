from datetime import date, datetime, timedelta
from dateutil.parser import parse

HOLIDAYS = [
    "2023-01-01", "2023-01-26", "2023-02-06", "2023-03-17", "2023-04-14",
    "2023-05-01", "2023-05-26", "2023-06-19", "2023-08-15", "2023-09-22",
    "2023-10-02", "2023-10-16", "2023-11-01", "2023-12-25"
]


def is_weekend(d):
    return d.weekday() >= 5


def is_holiday(d):
    return d.strftime("%Y-%m-%d") in HOLIDAYS


def calculate_leave_days(start_date, end_date, category, is_half_day=False):
    if isinstance(start_date, str):
        start_date = parse(start_date).date()
    elif isinstance(start_date, datetime):
        start_date = start_date.date()

    if isinstance(end_date, str):
        end_date = parse(end_date).date()
    elif isinstance(end_date, datetime):
        end_date = end_date.date()

    if category == "CL" and is_half_day:
        return 0.5

    days = (end_date - start_date).days + 1

    # BR-EL-011: For EL, COL, VL: continuous day counting (weekends/holidays count)
    if category in ["EL", "COL", "VL"]:
        return float(days)

    # For CL, SCL, RH: exclude weekends and holidays
    leave_days = 0.0
    for i in range(days):
        cur = start_date + timedelta(days=i)
        if not is_weekend(cur) and not is_holiday(cur):
            leave_days += 1.0

    return leave_days
