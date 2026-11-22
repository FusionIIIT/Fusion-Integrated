"""Pure leave-day counting rules adapted from the private ELM implementation."""

from datetime import date, datetime, timedelta
from decimal import Decimal

from modules.leave.domain.workflow import CL, COL, EL, RH, SCL, VL

CONTINUOUS_TYPES = frozenset({EL, COL, VL})


def count_days(
    leave_type: str,
    start: date,
    end: date,
    holidays: frozenset[date] = frozenset(),
    half_day: bool = False,
) -> Decimal:
    """Count inclusive leave days; weekends and holidays count for EL/COL/VL."""
    if (
        not isinstance(start, date)
        or isinstance(start, datetime)
        or not isinstance(end, date)
        or isinstance(end, datetime)
    ):
        raise ValueError("Start and end must be calendar dates.")  # noqa: TRY004
    if start > end:
        raise ValueError("The end date must not precede the start date.")
    if leave_type not in {CL, RH, SCL, EL, COL, VL}:
        raise ValueError("Unsupported leave category.")
    if half_day and (leave_type != CL or start != end):
        raise ValueError("A half-day leave must be one-day CL.")
    if leave_type in CONTINUOUS_TYPES:
        return Decimal((end - start).days + 1)
    if leave_type == RH:
        if start != end:
            raise ValueError("RH can only cover a single published restricted holiday.")
        return Decimal("1")

    current = start
    eligible_days = 0
    while current <= end:
        if current.weekday() < 5 and current not in holidays:
            eligible_days += 1
        current += timedelta(days=1)
    if eligible_days == 0:
        raise ValueError("CL and SCL must contain at least one eligible working day.")
    return Decimal("0.5") if half_day else Decimal(eligible_days)
