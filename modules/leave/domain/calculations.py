# Calculation rules for leave day counting (BR-EL-010, BR-EL-011)
from datetime import date, timedelta
from decimal import Decimal

from core.api.exceptions import BadRequestError
from modules.leave.domain.constants import (
    CONTINUOUS_COUNTING_LEAVE_TYPES,
    HALF_DAY_NONE,
    LEAVE_TYPE_CL,
    WORKING_DAY_COUNTING_LEAVE_TYPES,
)


def calculate_leave_days(
    leave_type: str,
    start_date: date,
    end_date: date,
    half_day: str = HALF_DAY_NONE,
) -> Decimal:
    """Calculate the number of leave days for a given period and leave type."""
    if end_date < start_date:
        raise BadRequestError("End date cannot be prior to start date.")

    if half_day != HALF_DAY_NONE:
        if leave_type != LEAVE_TYPE_CL:
            raise BadRequestError("Half-day leave is only permitted for Casual Leave (CL).")
        if start_date != end_date:
            raise BadRequestError("Half-day leave must have identical start and end dates.")
        return Decimal("0.5")

    if leave_type in CONTINUOUS_COUNTING_LEAVE_TYPES:
        total_days = (end_date - start_date).days + 1
        return Decimal(str(total_days))

    if leave_type in WORKING_DAY_COUNTING_LEAVE_TYPES:
        day_count = 0
        current = start_date
        while current <= end_date:
            # 5 is Saturday, 6 is Sunday
            if current.weekday() < 5:
                day_count += 1
            current += timedelta(days=1)
        if day_count == 0:
            raise BadRequestError("Selected leave dates only cover non-working weekend days.")
        return Decimal(str(day_count))

    raise BadRequestError(f"Unsupported leave type: {leave_type}")
