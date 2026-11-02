"""Pure Python business rules for Mess Management System (MMS).

Enforces BR-MMS-002, BR-MMS-009, BR-MMS-021, BR-MMS-022, and BR-MMS-023.
Zero framework imports permitted.
"""

from datetime import date
from typing import Any


def validate_rebate_request(start_date: date, end_date: date, submission_date: date) -> int:
    """Validate student rebate request duration and lead time.

    - BR-MMS-021: Minimum duration of 3 consecutive calendar days.
    - BR-MMS-022: Submitted at least 1 calendar day before start date.
    Returns the duration in days.
    """
    if start_date > end_date:
        raise ValueError("Rebate start date cannot be after end date.")

    # Calculate duration
    duration = (end_date - start_date).days
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
    """Enforce rebate non-overlap for the same student (BR-MMS-023).

    Rejects requests that conflict with any active or approved rebate.
    """
    for rebate in existing_rebates:
        status = rebate.get("status")
        if status in ["REJECTED", "rejected"]:
            continue

        ex_start = rebate["start_date"]
        ex_end = rebate["end_date"]
        if (new_start < ex_end) and (new_end > ex_start):
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
    """Validate student registration against an active window (BR-MMS-009)."""
    if not is_open:
        raise ValueError("The mess registration window is currently closed.")

    if not (window_start <= request_date <= window_end):
        raise ValueError(
            f"Registration request date ({request_date}) is outside the open window "
            f"({window_start} to {window_end})."
        )


def validate_role_assignment(role: str, employee_id: int) -> None:
    """Validate Caretaker/Warden role assignment (BR-MMS-002, BR-MMS-003, BR-MMS-004)."""
    valid_roles = {"caretaker", "warden"}
    if role not in valid_roles:
        raise ValueError(f"Invalid mess role '{role}'. Allowed roles: {valid_roles}")

    if not employee_id or employee_id <= 0:
        raise ValueError("Role assignment requires a valid positive employee_id.")
