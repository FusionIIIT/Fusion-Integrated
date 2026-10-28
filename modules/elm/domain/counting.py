"""Pure leave-day calculation rules derived from BR-EL-010/011.

Calendar exclusions are supplied explicitly by the caller, which keeps this
module independent of Django and makes the calculations deterministic.
"""

from datetime import date, timedelta
from decimal import Decimal

from modules.elm.domain.errors import InvalidLeaveRequest

CONTINUOUS_CATEGORIES = frozenset({"EL", "COL", "VL"})
CATEGORIES = frozenset({"CL", "RH", "SCL", "EL", "COL", "VL"})


def chargeable_days(
    category: str,
    start: date,
    end: date,
    *,
    closed_dates: set[date] | frozenset[date] = frozenset(),
    half_day: str = "none",
) -> Decimal:
    """Return chargeable days; continuous leave counts every intervening day.

    `closed_dates` includes weekends and published closed holidays for categories
    where those dates are excluded. For EL/COL/VL, every calendar day counts.
    CL half-days are represented as 0.5. RH/SCL are date-based, not continuous.
    """
    category = category.upper()
    if category not in CATEGORIES:
        raise InvalidLeaveRequest(f"Unsupported leave category: {category}")
    if end < start:
        raise InvalidLeaveRequest("Leave end date cannot precede its start date.")
    if half_day not in {"none", "first", "second"}:
        raise InvalidLeaveRequest("half_day must be none, first, or second.")
    if half_day != "none" and (category != "CL" or start != end):
        raise InvalidLeaveRequest("Half-day leave is supported only for single-day CL.")
    if half_day != "none":
        return Decimal("0.5")
    if category == "RH":
        # RH is selected from the published RH calendar; it is itself a holiday.
        return Decimal((end - start).days + 1)
    days = Decimal("0")
    current = start
    while current <= end:
        if category in CONTINUOUS_CATEGORIES or (
            current.weekday() < 5 and current not in closed_dates
        ):
            days += Decimal("1")
        current += timedelta(days=1)
    if days <= 0:
        raise InvalidLeaveRequest("The requested period contains no chargeable leave days.")
    return days


def intervals_overlap(a_start: date, a_end: date, b_start: date, b_end: date) -> bool:
    return a_start <= b_end and b_start <= a_end
