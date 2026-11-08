"""Pure business rules for Employee Leave Management (ELM).

This module deliberately has no Django or database dependencies.
"""

from datetime import date
from decimal import Decimal, InvalidOperation

VL_TO_EL_RATIO = Decimal("2")


class LeaveRuleError(ValueError):
    """Raised when a leave-domain rule is violated."""


def validate_date_range(start_date: date, end_date: date) -> None:
    """Require a valid inclusive leave date range."""
    if end_date < start_date:
        raise LeaveRuleError("End date cannot be before start date.")


def inclusive_calendar_days(start_date: date, end_date: date) -> int:
    """Count every calendar day in an inclusive date range."""
    validate_date_range(start_date, end_date)
    return (end_date - start_date).days + 1


def validate_sufficient_balance(
    available_balance: Decimal,
    requested_days: Decimal,
) -> None:
    """Reject negative requests and requests exceeding the balance."""
    try:
        available = Decimal(str(available_balance))
        requested = Decimal(str(requested_days))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise LeaveRuleError("Leave balances must be valid decimal numbers.") from exc

    if not available.is_finite() or not requested.is_finite():
        raise LeaveRuleError("Leave balances must be finite numbers.")

    if available < 0:
        raise LeaveRuleError("Available balance cannot be negative.")

    if requested <= 0:
        raise LeaveRuleError("Requested leave must be greater than zero.")

    if requested > available:
        raise LeaveRuleError("Insufficient leave balance.")


def convert_unused_vl_to_el(unused_vl: Decimal) -> Decimal:
    """Convert unused VL to EL at 2 VL : 1 EL, preserving fractions.

    The caller must separately credit the returned EL to the employee's
    EL balance and set the converted unused VL balance to zero.
    """
    try:
        vl = Decimal(str(unused_vl))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise LeaveRuleError("Unused VL must be a valid decimal number.") from exc

    if not vl.is_finite() or vl < 0:
        raise LeaveRuleError("Unused VL must be a finite, non-negative number.")

    return vl / VL_TO_EL_RATIO
