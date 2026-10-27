"""Leave-day calculations for categories with explicit counting rules."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

HalfDay = Literal["FIRST", "SECOND"]

_SUPPORTED_CATEGORIES = frozenset({"CL", "RH", "SCL", "EL", "COL", "VL"})
_CONTINUOUS_CATEGORIES = frozenset({"EL", "COL", "VL"})
_HALF_DAYS = frozenset({"FIRST", "SECOND"})


class LeaveDayCalculationError(ValueError):
    """Base exception for invalid or unsupported leave-day calculations."""


class InvalidLeaveDate(LeaveDayCalculationError):
    """Raised when dates are malformed or the interval is reversed."""


class UnsupportedLeaveCategory(LeaveDayCalculationError):
    """Raised when the requested leave category is not supported."""


class UnsupportedLeaveCountingRule(LeaveDayCalculationError):
    """Raised when a category/form has no specified counting rule here."""


class InvalidHalfDay(LeaveDayCalculationError):
    """Raised when half-day metadata is not FIRST or SECOND."""


def calculate_chargeable_days(
    start_date: date,
    end_date: date,
    leave_type: str,
    *,
    half_day: HalfDay | None = None,
) -> Decimal:
    """Return the chargeable quantity where the source defines its calculation.

    EL, COL, and VL use inclusive calendar-day counting. CL is supported only
    for a same-day first- or second-half request. Other category forms fail
    explicitly until their counting rules are defined.
    """
    if (
        not isinstance(start_date, date)
        or isinstance(start_date, datetime)
        or not isinstance(end_date, date)
        or isinstance(end_date, datetime)
    ):
        raise InvalidLeaveDate("start_date and end_date must be date values.")

    if start_date > end_date:
        raise InvalidLeaveDate("start_date must not be after end_date.")

    if not isinstance(leave_type, str) or leave_type not in _SUPPORTED_CATEGORIES:
        raise UnsupportedLeaveCategory(f"Unsupported leave category: {leave_type!r}.")

    if half_day is not None and (not isinstance(half_day, str) or half_day not in _HALF_DAYS):
        raise InvalidHalfDay("half_day must be FIRST, SECOND, or None.")

    if leave_type == "CL":
        if half_day is None:
            raise UnsupportedLeaveCountingRule(
                "CL full-day counting is not specified by this calculation."
            )
        if start_date != end_date:
            raise UnsupportedLeaveCountingRule("Only same-day CL half-day requests are supported.")
        return Decimal("0.5")

    if leave_type in {"RH", "SCL"}:
        raise UnsupportedLeaveCountingRule(
            f"The counting rule for {leave_type} is not specified here."
        )

    if half_day is not None:
        raise UnsupportedLeaveCountingRule(f"Half-day counting is not specified for {leave_type}.")

    if leave_type in _CONTINUOUS_CATEGORIES:
        return Decimal((end_date - start_date).days + 1)

    # The explicit category checks above make this unreachable unless the
    # supported categories and their rules drift apart.
    raise UnsupportedLeaveCountingRule(f"No counting rule is implemented for {leave_type}.")
