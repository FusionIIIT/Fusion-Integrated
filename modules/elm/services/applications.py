"""Application services: apply, withdraw, cancel, extend, resume."""

from __future__ import annotations

import datetime

from django.db import transaction

from modules.elm.domain.counting import calculate_chargeable_days
from modules.elm.domain.errors import InvalidDateRangeError, InvalidStateTransitionError
from modules.elm.domain.state_machine import determine_initial_state, transition_withdrawal
from modules.elm.domain.validation import (
    validate_available_balance,
    validate_category_and_dates,
    validate_non_overlapping,
    validate_restricted_holiday,
    validate_substitute,
    validate_vacation_period,
)
from modules.elm.models import LeaveApplication
from modules.elm.selectors.applications import get_active_leaves_for_user
from modules.elm.selectors.balances import (
    get_closed_holiday_dates,
    get_published_rh_dates,
    get_user_category_balance,
    get_vacation_periods,
)


@transaction.atomic
def apply_for_leave(
    user_id: int,
    leave_category: str,
    start_date: datetime.date,
    end_date: datetime.date,
    reason: str,
    half_day: bool = False,
    half_day_type: str = "",
    station_leave: bool = False,
    station_start_date: datetime.date | None = None,
    station_end_date: datetime.date | None = None,
    station_address: str = "",
    station_emergency_contact: str = "",
    substitute_required: bool = False,
    substitute_id: int | None = None,
    is_director: bool = False,
) -> LeaveApplication:
    """Submit a new leave application with complete domain validation (CW-EL-01)."""
    # 1. Basic validation
    validate_category_and_dates(
        category=leave_category,
        start_date=start_date,
        end_date=end_date,
        half_day=half_day,
        half_day_type=half_day_type,
    )

    # 2. Chargeable days calculation (BR-EL-010, BR-EL-011)
    closed_holidays = get_closed_holiday_dates(year=start_date.year)
    chargeable = calculate_chargeable_days(
        category=leave_category,
        start_date=start_date,
        end_date=end_date,
        half_day=half_day,
        closed_holidays=closed_holidays,
    )

    # 3. Available balance check (BR-EL-002..009)
    available = get_user_category_balance(
        user_id=user_id, category=leave_category, year=start_date.year
    )
    validate_available_balance(
        category=leave_category,
        chargeable_days=chargeable,
        available_balance=available,
    )

    # 4. Overlap validation (BR-EL-012)
    user_active_leaves = get_active_leaves_for_user(user_id=user_id)
    validate_non_overlapping(
        new_start=start_date,
        new_end=end_date,
        new_category=leave_category,
        new_half_day=half_day,
        new_half_day_type=half_day_type,
        existing_leaves=user_active_leaves,
    )

    # 5. Restricted Holiday calendar validation (BR-EL-003, BR-EL-031)
    if leave_category == "RH":
        published_rhs = get_published_rh_dates(year=start_date.year)
        validate_restricted_holiday(
            category=leave_category,
            start_date=start_date,
            published_rh_dates=published_rhs,
        )

    # 6. Vacation Leave vacation-period validation (BR-EL-006)
    if leave_category == "VL":
        vacations = get_vacation_periods(year=start_date.year)
        validate_vacation_period(
            category=leave_category,
            start_date=start_date,
            end_date=end_date,
            vacation_periods=vacations,
        )

    # 7. Substitute validation (BR-EL-014)
    if substitute_required and substitute_id is not None:
        sub_leaves = get_active_leaves_for_user(user_id=substitute_id)
        validate_substitute(
            applicant_id=user_id,
            substitute_id=substitute_id,
            start_date=start_date,
            end_date=end_date,
            substitute_leaves=sub_leaves,
        )

    # 8. Determine initial status (CW-EL-01)
    initial_status = determine_initial_state(
        substitute_required=substitute_required and substitute_id is not None,
        is_director=is_director,
    )

    return LeaveApplication.objects.create(
        user_id=user_id,
        leave_category=leave_category,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        chargeable_days=chargeable,
        half_day=half_day,
        half_day_type=half_day_type if half_day else "",
        station_leave=station_leave,
        station_start_date=station_start_date,
        station_end_date=station_end_date,
        station_address=station_address,
        station_emergency_contact=station_emergency_contact,
        substitute_required=substitute_required,
        substitute_id=substitute_id,
        substitute_status="pending" if (substitute_required and substitute_id) else "accepted",
        status=initial_status,
    )


@transaction.atomic
def withdraw_leave(application_id: int, user_id: int) -> LeaveApplication:
    """Withdraw a pending leave application immediately (BR-EL-022, BR-EL-034)."""
    app = LeaveApplication.objects.select_for_update().get(id=application_id, user_id=user_id)
    new_state = transition_withdrawal(app.status)
    app.status = new_state
    app.save(update_fields=["status", "updated_at"])
    return app


@transaction.atomic
def cancel_approved_leave(application_id: int, user_id: int, reason: str = "") -> LeaveApplication:
    """Request pre-start cancellation of approved leave (CW-EL-02, BR-EL-023)."""
    app = LeaveApplication.objects.select_for_update().get(id=application_id, user_id=user_id)
    if app.status != "approved":
        raise InvalidStateTransitionError("Only approved leave may be cancelled.")

    today = datetime.date.today()
    if today >= app.start_date:
        raise InvalidDateRangeError("Cancellation is only permitted prior to the start of leave.")

    app.status = "cancellation_pending_unit_head"
    app.reason = f"{app.reason}\n\n[Cancellation Request]: {reason}".strip()
    app.save(update_fields=["status", "reason", "updated_at"])
    return app


@transaction.atomic
def extend_ongoing_leave(
    application_id: int,
    user_id: int,
    extended_end_date: datetime.date,
    reason: str,
    substitute_id: int | None = None,
) -> LeaveApplication:
    """Request extension of ongoing EL, COL, or VL (CW-EL-03, BR-EL-025)."""
    app = LeaveApplication.objects.select_for_update().get(id=application_id, user_id=user_id)
    if app.status != "approved":
        raise InvalidStateTransitionError("Only approved leave may be extended.")

    if app.leave_category not in ("EL", "COL", "VL"):
        raise InvalidDateRangeError("Extension is only supported for EL, COL, or VL.")

    if extended_end_date <= app.end_date:
        raise InvalidDateRangeError("Extended end date must be after current end date.")

    # Calculate incremental additional days (BR-EL-025)
    incremental_start = app.end_date + datetime.timedelta(days=1)
    closed_holidays = get_closed_holiday_dates(year=incremental_start.year)
    incremental_days = calculate_chargeable_days(
        category=app.leave_category,
        start_date=incremental_start,
        end_date=extended_end_date,
        closed_holidays=closed_holidays,
    )

    # Validate balance for incremental days
    available = get_user_category_balance(
        user_id=user_id, category=app.leave_category, year=incremental_start.year
    )
    validate_available_balance(app.leave_category, incremental_days, available)

    # Create new extension record referencing original
    sub_required = substitute_id is not None
    initial_status = "awaiting_ext_substitute" if sub_required else "awaiting_ext_unit_head"

    return LeaveApplication.objects.create(
        user_id=user_id,
        leave_category=app.leave_category,
        start_date=incremental_start,
        end_date=extended_end_date,
        reason=f"[Extension of Leave #{app.id}]: {reason}",
        chargeable_days=incremental_days,
        substitute_required=sub_required,
        substitute_id=substitute_id,
        substitute_status="pending" if sub_required else "accepted",
        status=initial_status,
        original_application_id=app.id,
    )


@transaction.atomic
def submit_resumption(
    application_id: int,
    user_id: int,
    actual_resumption_date: datetime.date,
    resumption_reason: str = "",
) -> LeaveApplication:
    """Submit resumption of duty after returning from EL/COL/VL (CW-EL-04, BR-EL-027)."""
    app = LeaveApplication.objects.select_for_update().get(id=application_id, user_id=user_id)
    if app.status != "approved":
        raise InvalidStateTransitionError("Resumption can only be submitted for approved leaves.")

    if app.leave_category not in ("EL", "COL", "VL"):
        raise InvalidDateRangeError("Resumption review applies only to EL, COL, or VL.")

    app.resumption_date = actual_resumption_date
    app.resumption_reason = resumption_reason
    app.status = "resumption_review_pending"
    app.save(update_fields=["resumption_date", "resumption_reason", "status", "updated_at"])
    return app
