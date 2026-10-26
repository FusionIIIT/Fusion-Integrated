from datetime import date, timedelta


def calculate_leave_days(
    leave_type: str,
    start_date: date,
    end_date: date,
    is_half_day: bool = False,
    holidays: set[date] | None = None,
) -> float:
    """Calculates leave days based on Institute rules.
    - EL, COL, VL: continuous count across the interval (intervening weekends and holidays count).
    - CL, RH, SCL: working days only (weekends and listed holidays excluded).
    - Half-day CL: 0.5 day.
    """
    if is_half_day:
        return 0.5

    if start_date > end_date:
        return 0.0

    if leave_type in {"EL", "COL", "VL"}:
        return float((end_date - start_date).days + 1)

    holidays_set = holidays or set()
    total_days = 0.0
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() < 5 and current_date not in holidays_set:
            total_days += 1.0
        current_date += timedelta(days=1)
    return total_days


def validate_leave_application(
    leave_type: str,
    days: float,
    current_balance: float,
    has_overlap: bool = False,
) -> tuple[bool, str]:
    if has_overlap:
        return False, "Leave period overlaps with an existing leave request."
    if days <= 0:
        return False, "Invalid leave duration."
    if current_balance < days:
        return False, f"Insufficient leave balance. Available: {current_balance}, Requested: {days}"
    return True, ""
