# Validation rules for ELM applications (BR-EL-012, BR-EL-013, BR-EL-036)
from datetime import date
from decimal import Decimal

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.leave.domain.constants import (
    HALF_DAY_FIRST,
    HALF_DAY_NONE,
    HALF_DAY_SECOND,
    LEAVE_TYPE_CL,
)


def validate_station_leave(is_station_leave: bool, station_leave_address: str | None) -> None:
    """Enforce that station leave captures destination address (BR-EL-013)."""
    if is_station_leave and (not station_leave_address or not station_leave_address.strip()):
        raise BadRequestError("Station leave address is mandatory when station leave is requested.")


def is_half_day_complement(
    type_a: str,
    start_a: date,
    end_a: date,
    half_a: str,
    type_b: str,
    start_b: date,
    end_b: date,
    half_b: str,
) -> bool:
    """Return True if both applications are CL on the same single date occupying opposite halves."""
    if type_a != LEAVE_TYPE_CL or type_b != LEAVE_TYPE_CL:
        return False
    if start_a != end_a or start_b != end_b or start_a != start_b:
        return False
    if half_a == HALF_DAY_NONE or half_b == HALF_DAY_NONE:
        return False
    return (half_a == HALF_DAY_FIRST and half_b == HALF_DAY_SECOND) or (
        half_a == HALF_DAY_SECOND and half_b == HALF_DAY_FIRST
    )


def validate_leave_overlap(
    candidate_start: date,
    candidate_end: date,
    candidate_type: str,
    candidate_half: str,
    existing_applications: list,
) -> None:
    """Check for impermissible overlap against active applications (BR-EL-012)."""
    for app in existing_applications:
        app_start = app.start_date
        app_end = app.end_date

        if max(candidate_start, app_start) <= min(candidate_end, app_end):
            # Check half-day CL non-overlap exception
            if is_half_day_complement(
                candidate_type,
                candidate_start,
                candidate_end,
                candidate_half,
                app.leave_type,
                app_start,
                app_end,
                getattr(app, "half_day", HALF_DAY_NONE),
            ):
                continue
            raise ConflictError(
                f"Requested leave period overlaps with existing {app.status} application "
                f"(ID: {app.id}, {app_start} to {app_end})."
            )


def validate_balance_sufficiency(
    allocated: Decimal,
    used: Decimal,
    requested_days: Decimal,
    leave_type: str,
) -> None:
    """Ensure requested leave days do not exceed available balance."""
    available = allocated - used
    if requested_days > available:
        raise BadRequestError(
            f"Insufficient balance for {leave_type}. Required: {requested_days}, Left: {available}."
        )


def validate_approver_identity(applicant_user_id: int, approver_user_id: int) -> None:
    """Prevent self-approval of leave applications (BR-EL-036)."""
    if applicant_user_id == approver_user_id:
        raise PermissionDeniedError(
            "Approvers are strictly prohibited from approving their own leave applications."
        )
