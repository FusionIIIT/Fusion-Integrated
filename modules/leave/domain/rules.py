"""Pure Python implementation of HR-EIS Business Rules.

Traceable to:
- BR-HR-007: Required fields validation
- BR-HR-008: Balance and eligibility check
- BR-HR-009: Authority selection and hierarchical routing
- BR-HR-010: Automated leave balance update calculation
- BR-HR-023: Approval outcomes and workflow order invariants
- BR-HR-034: Supported leave types policy
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from modules.leave.domain.entities import (
    AuthorityRole,
    EmployeeCategory,
    LeaveType,
    ValidationResult,
)

SUPPORTED_LEAVE_TYPES = frozenset({
    LeaveType.CASUAL.value,
    LeaveType.RESTRICTED.value,
    LeaveType.MEDICAL.value,
    LeaveType.EARNED.value,
    LeaveType.VACATION.value,
    LeaveType.SABBATICAL.value,
})


def validate_required_fields(
    leave_type: str,
    start_date: date | None,
    end_date: date | None,
    duration_days: Decimal | None,
    justification: str | None,
) -> ValidationResult:
    """Validate mandatory fields per BR-HR-007 and BR-HR-034."""
    errors = []
    if not leave_type or leave_type not in SUPPORTED_LEAVE_TYPES:
        errors.append(f"Invalid or unsupported leave type: {leave_type!r}.")

    if start_date is None:
        errors.append("Start date is required.")
    if end_date is None:
        errors.append("End date is required.")
    if start_date and end_date and end_date < start_date:
        errors.append("End date cannot be prior to start date.")

    if duration_days is None or duration_days <= Decimal("0"):
        errors.append("Duration in days must be greater than zero.")

    if start_date and end_date and duration_days:
        calendar_days = Decimal(str((end_date - start_date).days + 1))
        if duration_days > calendar_days:
            errors.append(
                f"Duration ({duration_days} days) cannot exceed calendar range ({calendar_days} days)."
            )
        if duration_days < Decimal("1.0") and start_date != end_date:
            errors.append("Half-day leave must have identical start and end dates.")

    if not justification or not justification.strip():
        errors.append("Justification is mandatory before submission can be accepted.")

    return ValidationResult(is_valid=len(errors) == 0, errors=errors)


def validate_balance_and_eligibility(
    available_balance: Decimal,
    requested_days: Decimal,
) -> ValidationResult:
    """Validate leave balance sufficiency per BR-HR-008."""
    if available_balance < requested_days:
        return ValidationResult(
            is_valid=False,
            errors=[
                f"Insufficient leave balance: requested {requested_days} days, "
                f"but available balance is {available_balance} days."
            ],
        )
    return ValidationResult(is_valid=True)


def determine_approval_authority(
    employee_category: str,
    department: str = "",
    authority_directory: dict[str, int] | None = None,
) -> tuple[int | None, AuthorityRole]:
    """Determine initial approval authority tier per BR-HR-009.

    - Department-level approval routed to HOD where applicable.
    - Non-teaching staff routed to Registrar.
    - Faculty-level / final-authority routed to Director.
    """
    directory = authority_directory or {}

    cat = employee_category.lower()
    if cat == EmployeeCategory.STAFF.value:
        role = AuthorityRole.REGISTRAR
        user_id = directory.get("Registrar")
    elif cat == EmployeeCategory.FACULTY.value:
        # Default faculty routing: HOD for department evaluation, Director for final
        role = AuthorityRole.HOD
        dept_hod_key = f"HOD_{department}" if department else "HOD"
        user_id = directory.get(dept_hod_key) or directory.get("HOD") or directory.get("Director")
    else:
        # Student or general applicant
        role = AuthorityRole.HOD
        dept_hod_key = f"HOD_{department}" if department else "HOD"
        user_id = directory.get(dept_hod_key) or directory.get("HOD")

    return user_id, role


def calculate_balance_deduction(
    current_consumed: Decimal,
    current_available: Decimal,
    days: Decimal,
) -> tuple[Decimal, Decimal]:
    """Calculate updated consumed and available days upon approval per BR-HR-010."""
    new_consumed = current_consumed + days
    new_available = current_available - days
    return new_consumed, new_available


def determine_next_authority(
    current_role: str,
    employee_category: str = "staff",
    authority_directory: dict[str, int] | None = None,
) -> tuple[int | None, AuthorityRole | None]:
    """Determine next escalation authority for forwarding traversal (BW-HR-03).

    Routing hierarchy (BR-HR-009):
    HOD -> Director (for faculty) or Registrar (for staff)
    Registrar -> Director
    Director -> Terminal (no higher authority)
    """
    directory = authority_directory or {}
    cur = current_role.strip()

    if cur == AuthorityRole.HOD.value:
        if employee_category.lower() == EmployeeCategory.FACULTY.value:
            next_role = AuthorityRole.DIRECTOR
        else:
            next_role = AuthorityRole.REGISTRAR
    elif cur == AuthorityRole.REGISTRAR.value:
        next_role = AuthorityRole.DIRECTOR
    else:
        # Director is terminal
        return None, None

    next_id = directory.get(next_role.value)
    return next_id, next_role


def check_date_overlap(
    start1: date,
    end1: date,
    start2: date,
    end2: date,
) -> bool:
    """Return True if two date ranges overlap (inclusive)."""
    return not (end1 < start2 or end2 < start1)
