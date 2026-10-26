"""Services for creating, withdrawing, cancelling, and resuming leave applications."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from django.db import transaction

from modules.elm.domain.calculations import calculate_leave_days, check_date_overlap
from modules.elm.domain.entities import LeaveCategory, LeaveStatus
from modules.elm.domain.errors import (
    InsufficientBalanceError,
    InvalidLeaveTransitionError,
    LeaveValidationError,
)
from modules.elm.domain.state_machine import LeaveStateMachine
from modules.elm.models.leaves import LeaveRequest, LeaveTransitionHistory
from modules.elm.selectors.balances import get_user_balance_for_category
from modules.elm.selectors.holidays import get_closed_holiday_dates
from modules.elm.services.balances import (
    deduct_balance,
    refund_balance,
    seed_default_balances,
)


def apply_for_leave(
    *,
    user_id: int,
    category: str,
    start_date: date,
    end_date: date,
    reason: str,
    is_half_day: bool = False,
    half_day_period: str | None = None,
    leaving_station: bool = False,
    station_start_date: date | None = None,
    station_end_date: date | None = None,
    station_address: str = "",
    emergency_phone: str = "",
    substitute_user_id: int | None = None,
    unit_head_user_id: int | None = None,
    sanctioning_authority_user_id: int | None = None,
) -> LeaveRequest:
    """Validate and persist a new leave application in ELM."""
    if start_date > end_date:
        raise LeaveValidationError("Start date cannot be after end date.")

    if is_half_day and start_date != end_date:
        raise LeaveValidationError("Half-day leave must have identical start and end dates.")

    if not reason.strip():
        raise LeaveValidationError("A valid reason for leave is required.")

    # Calculate net days using domain rules
    closed_holidays = get_closed_holiday_dates(start_date.year)
    days_float = calculate_leave_days(
        category=category,
        start_date=start_date,
        end_date=end_date,
        is_half_day=is_half_day,
        half_day_period=half_day_period,
        closed_holidays=closed_holidays,
    )
    days_dec = Decimal(str(days_float))

    if days_dec <= Decimal("0.00"):
        raise LeaveValidationError("Calculated leave duration is 0 days. Check holiday or weekend calendar.")

    # Check that sufficient balance is available
    year = start_date.year
    bal = get_user_balance_for_category(user_id=user_id, year=year, category=category)
    if bal is None:
        seed_default_balances(user_id, year)
        bal = get_user_balance_for_category(user_id=user_id, year=year, category=category)

    if bal and bal.available_balance < days_dec:
        raise InsufficientBalanceError(
            f"Insufficient {category} quota: requested {days_dec} days, but available balance is {bal.available_balance} days."
        )

    # Overlap check: reject if any active/pending application already covers these dates (BR-EL-012)
    existing = LeaveRequest.objects.filter(
        user_id=user_id,
        status__in=[
            "awaiting_substitute",
            "substitute_declined",
            "awaiting_unit_head",
            "awaiting_sanction",
            "approved",
        ],
    )
    for existing_req in existing:
        if check_date_overlap(start_date, end_date, existing_req.start_date, existing_req.end_date):
            raise LeaveValidationError(
                f"Dates overlap with existing leave application #{existing_req.id} "
                f"({existing_req.start_date} \u2013 {existing_req.end_date}, status: {existing_req.status})."
            )

    # Determine initial status
    requires_substitute = substitute_user_id is not None and substitute_user_id > 0
    initial_status = LeaveStateMachine.submit_application(requires_substitute)

    with transaction.atomic():
        req = LeaveRequest.objects.create(
            user_id=user_id,
            category=category,
            start_date=start_date,
            end_date=end_date,
            is_half_day=is_half_day,
            half_day_period=half_day_period if is_half_day else None,
            days_calculated=days_dec,
            reason=reason.strip(),
            status=initial_status.value,
            leaving_station=leaving_station,
            station_start_date=station_start_date if leaving_station else None,
            station_end_date=station_end_date if leaving_station else None,
            station_address=station_address if leaving_station else "",
            emergency_phone=emergency_phone if leaving_station else "",
            substitute_user_id=substitute_user_id if requires_substitute else None,
            substitute_status="pending" if requires_substitute else "none",
            unit_head_user_id=unit_head_user_id,
            sanctioning_authority_user_id=sanctioning_authority_user_id,
        )

        LeaveTransitionHistory.objects.create(
            leave_request=req,
            from_status="draft",
            to_status=initial_status.value,
            actor_user_id=user_id,
            remarks="Application submitted.",
        )
        return req


def withdraw_leave(*, leave_id: int, actor_user_id: int) -> LeaveRequest:
    """Withdraw an in-flight leave request prior to final sanction."""
    with transaction.atomic():
        req = LeaveRequest.objects.select_for_update().get(pk=leave_id)
        current = LeaveStatus(req.status)
        result = LeaveStateMachine.withdraw(current)
        if not result.is_valid:
            raise InvalidLeaveTransitionError(result.message)

        prev_status = req.status
        req.status = result.next_status.value
        req.save(update_fields=["status", "updated_at"])

        LeaveTransitionHistory.objects.create(
            leave_request=req,
            from_status=prev_status,
            to_status=result.next_status.value,
            actor_user_id=actor_user_id,
            remarks="Application withdrawn by employee.",
        )
        return req


def cancel_approved_leave(
    *,
    leave_id: int,
    actor_user_id: int,
    remarks: str = "",
    today: date | None = None,
) -> LeaveRequest:
    """Pre-start cancellation: Employee cancels approved leave on or before start_date."""
    check_date = today or date.today()
    with transaction.atomic():
        req = LeaveRequest.objects.select_for_update().get(pk=leave_id)
        current = LeaveStatus(req.status)
        result = LeaveStateMachine.cancel_approved_leave(current, req.start_date, check_date)
        if not result.is_valid:
            raise InvalidLeaveTransitionError(result.message)

        prev_status = req.status
        req.status = result.next_status.value
        req.save(update_fields=["status", "updated_at"])

        # Refund the availed days back into the employee's ledger
        refund_balance(
            user_id=req.user_id,
            year=req.start_date.year,
            category=req.category,
            days=float(req.days_calculated),
            reason=f"Refund from cancelled Leave #{req.id}: {remarks or 'Pre-start cancellation'}",
        )

        LeaveTransitionHistory.objects.create(
            leave_request=req,
            from_status=prev_status,
            to_status=result.next_status.value,
            actor_user_id=actor_user_id,
            remarks=remarks or "Approved leave cancelled prior to start date.",
        )
        return req


def resume_duty(
    *,
    leave_id: int,
    actor_user_id: int,
    actual_resumption_date: date,
    remarks: str = "",
) -> LeaveRequest:
    """Confirm employee duty resumption following leave completion."""
    with transaction.atomic():
        req = LeaveRequest.objects.select_for_update().get(pk=leave_id)
        current = LeaveStatus(req.status)
        result = LeaveStateMachine.submit_resumption(current)
        if not result.is_valid:
            raise InvalidLeaveTransitionError(result.message)

        prev_status = req.status
        req.status = result.next_status.value
        req.actual_resumption_date = actual_resumption_date
        req.resumption_remarks = remarks
        req.save(update_fields=["status", "actual_resumption_date", "resumption_remarks", "updated_at"])

        LeaveTransitionHistory.objects.create(
            leave_request=req,
            from_status=prev_status,
            to_status=result.next_status.value,
            actor_user_id=actor_user_id,
            remarks=f"Duty resumed on {actual_resumption_date}. {remarks}".strip(),
        )
        return req
