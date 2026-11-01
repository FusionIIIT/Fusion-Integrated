"""Pure Python business rules for Mess Management System (MMS).

Implements BR-MMS-001 through BR-MMS-042.
No Django, DRF or Celery imports permitted.
"""
from datetime import date
from typing import Any

from modules.mms.domain.constants import MessRole, RebateStatus


def validate_rebate_request(start_date: date, end_date: date, submission_date: date) -> int:
    """Validate student rebate request parameters.

    BR-MMS-021: Minimum rebate duration of 3 days.
    BR-MMS-022: Submitted at least one calendar day before rebate start date.
    Returns: duration in days.
    """
    if start_date > end_date:
        raise ValueError("Rebate start date cannot be after end date.")

    duration = (end_date - start_date).days + 1
    if duration < 3:
        raise ValueError(
            "MMS rejects rebate requests with duration fewer than 3 days "
            f"(requested: {duration} days)."
        )

    if start_date <= submission_date:
        raise ValueError(
            "Rebate request must be submitted at least one calendar day before "
            f"start date {start_date} (submitted on {submission_date})."
        )

    return duration


def check_rebate_overlap(
    existing_rebates: list[dict[str, Any]],
    new_start: date,
    new_end: date,
) -> None:
    """Validate rebate non-overlap per BR-MMS-023.

    MMS prevents overlapping active or approved rebate requests for the same student.
    """
    for rebate in existing_rebates:
        status = rebate.get("status")
        if status == RebateStatus.REJECTED.value:
            continue

        ex_start = rebate["start_date"]
        ex_end = rebate["end_date"]
        if (new_start <= ex_end) and (new_end >= ex_start):
            raise ValueError(
                f"Requested rebate ({new_start} to {new_end}) impermissibly overlaps with existing "
                f"rebate #{rebate.get('id')} ({ex_start} to {ex_end}, status: {status})."
            )


def validate_registration_window(
    window_start: date,
    window_end: date,
    request_date: date,
    is_open: bool,
) -> None:
    """Validate registration window per BR-MMS-009.

    Student registration requests must fall within an open registration window.
    """
    if not is_open:
        raise ValueError("The mess registration window is currently closed.")

    if not (window_start <= request_date <= window_end):
        raise ValueError(
            f"Registration request date ({request_date}) is outside the open window "
            f"({window_start} to {window_end})."
        )


def validate_role_assignment(role: str, employee_id: int) -> None:
    """Validate operational role assignment per BR-MMS-002, BR-MMS-003, BR-MMS-004.

    Role must be Caretaker or Warden and assigned to a valid employee.
    """
    valid_roles = {MessRole.CARETAKER.value, MessRole.WARDEN.value}
    if role not in valid_roles:
        raise ValueError(f"Invalid mess role '{role}'. Allowed roles: {valid_roles}")

    if not employee_id or employee_id <= 0:
        raise ValueError("Role assignment requires a valid positive employee_id.")

