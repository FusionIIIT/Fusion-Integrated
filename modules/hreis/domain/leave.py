"""Leave domain logic (BR-HR-007, BR-HR-008, BR-HR-010, BR-HR-034)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from modules.hreis.domain.exceptions import DomainValidationError


class LeaveType(str, Enum):
    CASUAL = "casual"
    RESTRICTED = "restricted"
    MEDICAL = "medical"
    EARNED = "earned"
    VACATION = "vacation"
    SABBATICAL = "sabbatical"


class LeaveStatus(str, Enum):
    PENDING = "pending"
    FORWARDED = "forwarded"
    APPROVED = "approved"
    REJECTED = "rejected"


DEFAULT_LEAVE_QUOTAS: dict[str, float] = {
    LeaveType.CASUAL.value: 8.0,
    LeaveType.RESTRICTED.value: 2.0,
    LeaveType.MEDICAL.value: 15.0,
    LeaveType.EARNED.value: 30.0,
    LeaveType.VACATION.value: 60.0,
    LeaveType.SABBATICAL.value: 365.0,
}



def validate_leave_submission(
    *,
    leave_type: str,
    start_date: date,
    end_date: date,
    duration_days: float,
    justification: str,
    category: str,
    current_balances: dict[str, float],
) -> None:
    """Validate leave request requirements prior to acceptance (BR-HR-007, BR-HR-008)."""
    valid_types = {t.value for t in LeaveType}
    if leave_type not in valid_types:
        raise DomainValidationError(
            f"Invalid leave type '{leave_type}'. Supported types: {', '.join(sorted(valid_types))}."
        )

    if end_date < start_date:
        raise DomainValidationError("End date cannot precede start date.")

    if duration_days <= 0:
        raise DomainValidationError("Leave duration must be greater than zero.")

    if not justification or not justification.strip():
        raise DomainValidationError("Leave justification is required.")

    # Sabbatical rule: faculty only
    if leave_type == LeaveType.SABBATICAL.value and category != "faculty":
        raise DomainValidationError("Sabbatical leave is only eligible for faculty.")

    available_balance = current_balances.get(leave_type, 0.0)
    if duration_days > available_balance:
        raise DomainValidationError(
            f"Insufficient leave balance for {leave_type}. "
            f"Requested: {duration_days}, Available: {available_balance}."
        )


def calculate_new_balance(
    current_balances: dict[str, float],
    leave_type: str,
    duration_days: float,
) -> dict[str, float]:
    """Deduct leave balance upon approval (BR-HR-010)."""
    new_balances = dict(current_balances)
    current = new_balances.get(leave_type, 0.0)
    new_balances[leave_type] = max(0.0, round(current - duration_days, 1))
    return new_balances
