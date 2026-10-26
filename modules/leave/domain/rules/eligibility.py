"""Leave eligibility rules — pure Python, no Django imports."""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from .entities import LeaveCategory, EmployeeType, LeaveEntitlement, LeaveBalance


@dataclass(frozen=True)
class EligibilityResult:
    eligible: bool
    reason: str
    max_days_allowed: Optional[float] = None


def check_eligibility(
    user_id: int,
    category: LeaveCategory,
    employee_type: EmployeeType,
    requested_days: float,
    start_date: date,
    end_date: date,
    current_balance: LeaveBalance,
    policy: LeaveEntitlement,
    has_medical_certificate: bool = False,
    overlapping_requests: int = 0,
) -> EligibilityResult:
    """Check if user is eligible for the leave request."""
    # Check category eligibility for employee type
    if category == LeaveCategory.VL and employee_type != EmployeeType.FACULTY:
        return EligibilityResult(False, "Vacation Leave is only for faculty")

    if category == LeaveCategory.COL and employee_type != EmployeeType.NON_FACULTY:
        return EligibilityResult(False, "Commuted Leave is only for non-faculty")

    # Check balance
    available = current_balance.closing_balance
    if requested_days > available:
        return EligibilityResult(
            False,
            f"Insufficient {category.value} balance. Available: {available}, Requested: {requested_days}",
            max_days_allowed=available,
        )

    # Check half-day for CL
    if category == LeaveCategory.CL:
        if requested_days % 0.5 != 0:
            return EligibilityResult(False, "CL must be in half-day increments")

    # Check medical certificate for COL
    if category == LeaveCategory.COL and not has_medical_certificate:
        return EligibilityResult(False, "Medical certificate required for Commuted Leave")

    # Check overlapping requests
    if overlapping_requests > 0:
        return EligibilityResult(False, "Overlapping leave request exists")

    # Check max per request
    if policy.max_per_request and requested_days > policy.max_per_request:
        return EligibilityResult(
            False,
            f"Maximum {policy.max_per_request} days allowed per request",
            max_days_allowed=policy.max_per_request,
        )

    return EligibilityResult(True, "Eligible")


def calculate_leave_days(
    category: LeaveCategory,
    start_date: date,
    end_date: date,
    half_day: bool = False,
    half_day_session: Optional[str] = None,
    holidays: list[date] = None,
    weekends: list[int] = None,
) -> float:
    """Calculate leave days based on category rules."""
    if half_day:
        return 0.5

    days = (end_date - start_date).days + 1

    # For CL, SCL, RH - only count working days
    if category in (LeaveCategory.CL, LeaveCategory.SCL, LeaveCategory.RH):
        # This is simplified - real implementation would check actual calendar
        working_days = 0
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:  # Mon-Fri
                if holidays and current in holidays:
                    current += timedelta(days=1)
                    continue
                working_days += 1
            current += timedelta(days=1)
        return working_days

    # For EL, VL, COL - count all days including weekends/holidays
    return float(days)


def year_end_processing(
    category: LeaveCategory,
    employee_type: EmployeeType,
    current_balance: LeaveBalance,
) -> tuple[float, float, float]:
    """Calculate year-end balance adjustments.

    Returns (lapsed_days, carried_forward_days, el_credited_from_vl)
    """
    if category == LeaveCategory.CL or category == LeaveCategory.RH:
        # Lapses completely
        return current_balance.closing_balance, 0.0, 0.0

    if category == LeaveCategory.SCL:
        # Does not carry forward
        return current_balance.closing_balance, 0.0, 0.0

    if category == LeaveCategory.EL:
        # Carries forward fully
        return 0.0, current_balance.closing_balance, 0.0

    if category == LeaveCategory.COL:
        # Carries forward fully
        return 0.0, current_balance.closing_balance, 0.0

    if category == LeaveCategory.VL and employee_type == EmployeeType.FACULTY:
        # 2 VL : 1 EL conversion
        vl_to_convert = current_balance.closing_balance
        el_credited = vl_to_convert / 2.0
        return vl_to_convert, 0.0, el_credited

    return 0.0, 0.0, 0.0


from datetime import timedelta