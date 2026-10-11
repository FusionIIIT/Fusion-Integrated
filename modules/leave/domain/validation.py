"""Domain validation rules for Employee Leave Management.

Pure Python — no framework imports.
Enforces BR-EL-001, BR-EL-003, BR-EL-006, BR-EL-012, BR-EL-013, BR-EL-014, BR-EL-023, BR-EL-025.
"""

from collections.abc import Sequence
from datetime import date, timedelta
from decimal import Decimal

from modules.leave.domain.constants import HalfDay, LeaveCategory
from modules.leave.domain.exceptions import (
    InsufficientBalanceError,
    InvalidSubstituteError,
    LeaveOverlapError,
    PolicyViolationError,
)


def validate_category_eligibility(category: str, employee_kind: str) -> None:
    """Enforces BR-EL-001, BR-EL-005, BR-EL-006."""
    if category not in LeaveCategory:
        raise PolicyViolationError(f"Unsupported leave category: {category}")

    if category == LeaveCategory.VL and employee_kind != "faculty":
        raise PolicyViolationError("Vacation Leave (VL) is admissible only for faculty members.")


def validate_rh_dates(
    requested_dates: Sequence[date],
    published_rh_dates: set[date],
) -> None:
    """Enforces BR-EL-003: RH requests must match published Restricted Holidays."""
    for d in requested_dates:
        if d not in published_rh_dates:
            raise PolicyViolationError(
                f"Date {d.isoformat()} is not a published Restricted Holiday "
                f"in the current calendar."
            )


def validate_vl_dates(
    start_date: date,
    end_date: date,
    vacation_periods: Sequence[tuple[date, date]],
) -> None:
    """Enforces BR-EL-006: VL must fall entirely within configured vacation periods."""
    in_vacation = any(
        vac_start <= start_date and end_date <= vac_end for vac_start, vac_end in vacation_periods
    )
    if not in_vacation:
        raise PolicyViolationError(
            "Vacation Leave must fall entirely within an approved Academic "
            "Calendar vacation period."
        )


def validate_balance(available_balance: Decimal, required_days: Decimal, category: str) -> None:
    """Enforces entitlement balance checks for all categories."""
    if available_balance < required_days:
        raise InsufficientBalanceError(
            f"Insufficient {category} balance. Available: {available_balance}, "
            f"required: {required_days}."
        )


def validate_non_overlap(
    start_date: date,
    end_date: date,
    half_day: str,
    active_intervals: Sequence[tuple[date, date, str]],
) -> None:
    """Enforces BR-EL-012: Non-overlap with applicant's active pending or approved leave.

    active_intervals is a list of (existing_start, existing_end, existing_half_day).
    First-half and second-half CL on the same date are allowed.
    """
    for ex_start, ex_end, ex_half in active_intervals:
        # Check date intersection
        if max(start_date, ex_start) <= min(end_date, ex_end):
            # Same single date and different halves exception
            if (
                start_date == end_date == ex_start == ex_end
                and half_day in (HalfDay.FIRST_HALF, HalfDay.SECOND_HALF)
                and ex_half in (HalfDay.FIRST_HALF, HalfDay.SECOND_HALF)
                and half_day != ex_half
            ):
                continue
            raise LeaveOverlapError(
                f"Requested leave period ({start_date} to {end_date}) overlaps "
                f"with an existing leave ({ex_start} to {ex_end})."
            )


def validate_substitute(
    applicant_user_id: int,
    substitute_user_id: int | None,
    substitute_active_intervals: Sequence[tuple[date, date]],
    start_date: date,
    end_date: date,
) -> None:
    """Enforces BR-EL-014: Substitute eligibility."""
    if substitute_user_id is None:
        return
    if substitute_user_id == applicant_user_id:
        raise InvalidSubstituteError("An employee cannot nominate themselves as substitute.")

    for sub_start, sub_end in substitute_active_intervals:
        if max(start_date, sub_start) <= min(end_date, sub_end):
            raise InvalidSubstituteError(
                "The nominated substitute has an overlapping pending or approved "
                "leave during this period."
            )


def validate_station_leave(
    station_leave_applied: bool,
    station_details: dict | None,
) -> None:
    """Enforces BR-EL-013: Station Leave coupling."""
    if not station_leave_applied:
        return
    if not station_details or not station_details.get("station_address"):
        raise PolicyViolationError("Station address is required when applying for Station Leave.")


def validate_cancellation_pre_start(start_date: date, current_date: date) -> None:
    """Enforces BR-EL-023: Cancellation before start of approved leave."""
    if current_date >= start_date:
        raise PolicyViolationError(
            "Approved leave cannot be cancelled once the leave start date has arrived. "
            "Use extension or resumption instead."
        )


def validate_extension_eligibility(
    category: str,
    original_start: date,
    original_end: date,
    extension_start: date,
    extension_end: date,
    current_date: date,
) -> None:
    """Enforces BR-EL-025: Extension of ongoing EL/COL/VL."""
    if category not in (LeaveCategory.EL, LeaveCategory.COL, LeaveCategory.VL):
        raise PolicyViolationError("Extensions are only permitted for ongoing EL, COL, or VL.")
    if not (original_start <= current_date <= original_end):
        raise PolicyViolationError(
            "Leave extension can only be requested while the leave is currently ongoing."
        )
    if extension_start != original_end + timedelta(days=1):
        raise PolicyViolationError(
            "Extension period must begin immediately the day after current leave end date."
        )
    if extension_start > extension_end:
        raise PolicyViolationError("Extension end date must be on or after extension start date.")
