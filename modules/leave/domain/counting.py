from datetime import date, timedelta
from decimal import Decimal

from modules.leave.domain.workflow import CL, COL, EL, RH, VL

CONTINUOUS_TYPES = frozenset({EL, COL, VL})


def count_days(leave_type: str, start: date, end: date,
               holidays: frozenset[date] = frozenset(), half_day: bool = False) -> Decimal:
    if start > end:
        raise ValueError("The end date must not precede the start date.")
    if leave_type in CONTINUOUS_TYPES:
        count = (end - start).days + 1
    elif leave_type == RH:
        count = 1
    else:
        count = 0
        current = start
        while current <= end:
            if current.weekday() < 5 and current not in holidays:
                count += 1
            current += timedelta(days=1)
    if half_day and leave_type == CL and start == end:
        return Decimal("0.5")
    return Decimal(count)
