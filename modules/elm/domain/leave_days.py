from datetime import date, timedelta
from decimal import Decimal


def count_leave_days(start: date, end: date, part_of_day: str = "full") -> Decimal:
    """Working days (Mon-Fri) in the range. A half day must be a single day."""
    if end < start:
        raise ValueError("end date is before start date")
    if part_of_day != "full":
        if start != end:
            raise ValueError("a half day must be a single day")
        return Decimal("0.5") if start.weekday() < 5 else Decimal("0")
    span = (end - start).days + 1
    working = sum(1 for i in range(span) if (start + timedelta(days=i)).weekday() < 5)
    return Decimal(working)
