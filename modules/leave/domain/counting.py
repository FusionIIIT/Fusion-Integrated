import datetime
from decimal import Decimal
from typing import Set, Optional, Union
from modules.leave.domain.categories import CL, RH, CONTINUOUS_COUNT_CATEGORIES

def _to_date(d: Union[str, datetime.date, None]) -> Optional[datetime.date]:
    if d is None:
        return None
    if isinstance(d, datetime.date):
        return d
    return datetime.date.fromisoformat(str(d))

def calculate_leave_days(
    category: str,
    start_date: Union[str, datetime.date],
    end_date: Union[str, datetime.date, None],
    half_day_type: str = "full",
    closed_holidays: Optional[Set[datetime.date]] = None,
    rh_holidays: Optional[Set[datetime.date]] = None,
) -> Decimal:
    if end_date is None:
        raise ValueError("End date cannot be None.")
    start = _to_date(start_date)
    end = _to_date(end_date)
    if end < start:
        raise ValueError("End date cannot be earlier than start date.")

    closed_holidays = {_to_date(h) for h in (closed_holidays or set())}
    rh_holidays = {_to_date(h) for h in (rh_holidays or set())}

    if half_day_type in ("first_half", "second_half"):
        if category != CL:
            raise ValueError("Half-day leave is only permitted for Casual Leave (CL).")
        if start != end:
            raise ValueError("Half-day leave must start and end on the same single date.")
        return Decimal("0.5")

    if category in CONTINUOUS_COUNT_CATEGORIES:
        return Decimal((end - start).days + 1)

    if category == RH:
        if start != end:
            raise ValueError("Restricted Holiday must be taken 1 day at a time.")
        if start not in rh_holidays and str(start) not in rh_holidays:
            raise ValueError("Date is not an active Restricted Holiday (RH).")
        return Decimal("1.0")

    # Working days for CL, SCL
    total_days = 0
    curr = start
    one_day = datetime.timedelta(days=1)
    while curr <= end:
        if curr.weekday() < 5 and curr not in closed_holidays:
            total_days += 1
        curr += one_day

    if total_days == 0:
        raise ValueError("Selected dates fall entirely on weekends or closed holidays.")

    return Decimal(str(total_days))