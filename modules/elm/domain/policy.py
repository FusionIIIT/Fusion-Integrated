from datetime import date
from decimal import Decimal

from modules.elm.domain.entities import (
    LeaveCategory,
    LeaveRequestDateRange,
)


_CONTINUOUS_CATEGORIES = (
    LeaveCategory.EL,
    LeaveCategory.COL,
    LeaveCategory.VL,
)


def count_continuous_leave_days(
    category: LeaveCategory,
    date_range: LeaveRequestDateRange,
) -> int:
    """Count inclusive calendar days for EL, COL, or VL."""
    if not isinstance(category, LeaveCategory):
        raise TypeError("category must be a LeaveCategory")

    if not isinstance(date_range, LeaveRequestDateRange):
        raise TypeError("date_range must be a LeaveRequestDateRange")

    if type(date_range.start_date) is not date or type(date_range.end_date) is not date:
        raise TypeError("date range boundaries must be dates")

    if category not in _CONTINUOUS_CATEGORIES:
        raise ValueError(
            f"{category.value} does not use continuous leave counting"
        )

    return (date_range.end_date - date_range.start_date).days + 1


def validate_sufficient_balance(
    available_balance: int | Decimal,
    requested_days: int | Decimal,
) -> None:
    """Raise an error when requested leave exceeds the available balance."""
    values = (
        ("available_balance", available_balance),
        ("requested_days", requested_days),
    )

    for name, value in values:
        if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
            raise TypeError(f"{name} must be an integer or Decimal")

        if isinstance(value, Decimal) and not value.is_finite():
            raise ValueError(f"{name} must be finite")

        if value < 0:
            raise ValueError(f"{name} cannot be negative")

    available = Decimal(available_balance)
    requested = Decimal(requested_days)

    if requested > available:
        from modules.elm.domain.errors import InsufficientBalanceError
        raise InsufficientBalanceError(available, requested)

    return None



def get_annual_limit(
    category: LeaveCategory,
    *,
    is_faculty: bool | None = None,
    col_eligible: bool | None = None,
) -> Decimal:
    """Return the documented annual limit for a leave category.

    SCL's value is a maximum, not an automatic grant.
    COL requires explicit eligibility.
    """
    if not isinstance(category, LeaveCategory):
        raise TypeError("category must be a LeaveCategory")

    fixed_limits = {
        LeaveCategory.CL: Decimal("8"),
        LeaveCategory.RH: Decimal("2"),
        LeaveCategory.SCL: Decimal("15"),
    }
    if category in fixed_limits:
        return fixed_limits[category]

    if category in (LeaveCategory.EL, LeaveCategory.VL):
        if not isinstance(is_faculty, bool):
            raise TypeError("is_faculty must be a bool for EL/VL")

        if category is LeaveCategory.EL:
            if is_faculty:
                raise ValueError("Faculty EL limit is unspecified")
            return Decimal("30")

        if not is_faculty:
            raise ValueError("VL is applicable to faculty only")
        return Decimal("60")

    if category is LeaveCategory.COL:
        if not isinstance(col_eligible, bool):
            raise TypeError("col_eligible must be a bool for COL")
        if not col_eligible:
            raise ValueError("Employee is not eligible for COL")
        return Decimal("20")

    raise ValueError(f"No annual limit defined for {category!r}")


def validate_category_eligibility(
    category: LeaveCategory,
    *,
    is_faculty: bool | None = None,
    col_eligible: bool | None = None,
) -> None:
    """Raise IneligibleCategoryError when the employee cannot use a category."""
    from modules.elm.domain.errors import IneligibleCategoryError

    if not isinstance(category, LeaveCategory):
        raise TypeError("category must be a LeaveCategory")

    if category is LeaveCategory.VL:
        if not isinstance(is_faculty, bool):
            raise TypeError("is_faculty must be a bool for VL")
        if not is_faculty:
            raise IneligibleCategoryError(category.value)

    elif category is LeaveCategory.COL:
        if not isinstance(col_eligible, bool):
            raise TypeError("col_eligible must be a bool for COL")
        if not col_eligible:
            raise IneligibleCategoryError(category.value)

    return None
