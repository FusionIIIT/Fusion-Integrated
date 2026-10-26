from datetime import timedelta
from decimal import Decimal


def count_leave_days(category, start_date, end_date, half_day, holidays):
    if end_date < start_date:
        raise ValueError("End date must be after start date")

    days = 0

    for day in range((end_date - start_date).days + 1):
        current_date = start_date + timedelta(days=day)
        if category == 'CL':
            days += Decimal('0.5') if half_day and current_date == start_date else Decimal('1')
        elif category in ('EL', 'COL', 'VL'):
            days += 1
        else:
            days += 1

    return Decimal(days)
