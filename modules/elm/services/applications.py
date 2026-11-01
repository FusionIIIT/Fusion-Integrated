"""Leave Application submission and withdrawal services."""
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from modules.elm.domain.calculations import calculate_leave_days, check_date_overlap
from modules.elm.domain.state_machine import LeaveStateMachine
from modules.elm.models.balances import LeaveBalance
from modules.elm.models.holidays import HolidayCalendar
from modules.elm.models.leaves import LeaveRequest, LeaveTransitionHistory


@transaction.atomic
def apply_for_leave(
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
    is_director: bool = False,
) -> LeaveRequest:
    """Submit a new leave application (CW-EL-01, EL-UC-001)."""
    if start_date > end_date:
        raise ValueError("Start date cannot be after end date.")

    # 1. Check for overlapping pending or approved leave (BR-EL-012)
    existing_leaves = LeaveRequest.objects.filter(
        user_id=user_id,
        status__in=[
            "awaiting_substitute", "substitute_declined", "awaiting_unit_head",
            "awaiting_establishment",
            "awaiting_final_sanction", "approved",
        ],
    )
    for existing in existing_leaves:
        if check_date_overlap(
            start1=start_date, end1=end_date,
            is_half1=is_half_day, period1=half_day_period,
            start2=existing.start_date, end2=existing.end_date,
            is_half2=existing.is_half_day, period2=existing.half_day_period,
        ):
            raise ValueError(f"Requested leave conflicts with existing {existing.category} leave (#{existing.id}).")

    # 2. Check substitute eligibility (BR-EL-014)
    if substitute_user_id:
        if substitute_user_id == user_id:
            raise ValueError("Applicant cannot nominate themselves as substitute.")
        # Check if substitute has conflicting leave
        sub_conflict = LeaveRequest.objects.filter(
            user_id=substitute_user_id,
            status="approved",
            start_date__lte=end_date,
            end_date__gte=start_date,
        ).exists()
        if sub_conflict:
            raise ValueError("Nominated substitute has approved leave during this period.")

    # 3. Calculate leave days
    closed_holidays = set(HolidayCalendar.objects.filter(
        holiday_type="closed",
        year=start_date.year,
        is_published=True,
    ).values_list("date", flat=True))

    days = calculate_leave_days(
        category=category,
        start_date=start_date,
        end_date=end_date,
        is_half_day=is_half_day,
        half_day_period=half_day_period,
        closed_holidays=closed_holidays,
    )

    # 4. Check available balance (BR-EL-002 - BR-EL-009)
    balance_record = LeaveBalance.objects.filter(
        user_id=user_id,
        year=start_date.year,
        category=category,
    ).first()

    available = balance_record.available_balance if balance_record else Decimal("0.00")
    if Decimal(str(days)) > available:
        raise ValueError(f"Insufficient {category} balance. Required: {days}, Available: {available}.")

    # 5. Determine initial state via state machine
    requires_sub = bool(substitute_user_id)
    initial_status = LeaveStateMachine.submit_application(
        requires_substitute=requires_sub,
        is_director=is_director,
    )

    req = LeaveRequest.objects.create(
        user_id=user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        is_half_day=is_half_day,
        half_day_period=half_day_period,
        days_calculated=Decimal(str(days)),
        reason=reason,
        status=initial_status.value,
        leaving_station=leaving_station,
        station_start_date=station_start_date,
        station_end_date=station_end_date,
        station_address=station_address,
        emergency_phone=emergency_phone,
        substitute_user_id=substitute_user_id,
        substitute_status="pending" if requires_sub else "none",
        unit_head_user_id=unit_head_user_id,
    )

    LeaveTransitionHistory.objects.create(
        leave_request=req,
        from_status="draft",
        to_status=initial_status.value,
        actor_user_id=user_id,
        remarks="Application submitted.",
    )

    return req


@transaction.atomic
def withdraw_leave_application(user_id: int, leave_id: int) -> LeaveRequest:
    """Immediately withdraw a pending leave request (CW-EL-01, EL-UC-007, BR-EL-022)."""
    req = LeaveRequest.objects.select_for_update().filter(user_id=user_id, pk=leave_id).first()
    if not req:
        raise ValueError("Leave application not found.")

    res = LeaveStateMachine.withdraw_pending(req.status)
    if not res.success:
        raise ValueError(res.message)

    old_status = req.status
    req.status = res.new_status.value
    req.save(update_fields=["status", "updated_at"])

    LeaveTransitionHistory.objects.create(
        leave_request=req,
        from_status=old_status,
        to_status=req.status,
        actor_user_id=user_id,
        remarks="Withdrawn by applicant.",
    )

    return req


@transaction.atomic
def request_leave_extension(
    user_id: int,
    leave_id: int,
    end_date: date,
    reason: str,
    substitute_user_id: int | None = None,
) -> LeaveRequest:
    """Submit an extension request for an ongoing EL, COL, or VL leave."""
    original = LeaveRequest.objects.select_for_update().filter(
        user_id=user_id, pk=leave_id, status="approved", is_extension=False
    ).first()
    if not original:
        raise ValueError("Ongoing approved leave was not found.")
    if original.category not in {"EL", "COL", "VL"}:
        raise ValueError("Only EL, COL, and VL leave can be extended.")

    today = timezone.localdate()
    if not original.start_date <= today <= original.end_date:
        raise ValueError("An extension can only be requested while the leave is ongoing.")
    if end_date <= original.end_date:
        raise ValueError("Extension end date must be after the approved end date.")

    extension_start = original.end_date + timedelta(days=1)
    active_statuses = [
        "awaiting_substitute", "substitute_declined", "awaiting_unit_head",
        "awaiting_establishment",
        "awaiting_final_sanction", "approved", "extension_pending_substitute",
        "extension_applicant_action_required", "extension_pending_unit_head",
        "extension_pending_establishment", "extension_pending_final",
    ]
    for existing in LeaveRequest.objects.filter(user_id=user_id, status__in=active_statuses):
        if check_date_overlap(
            start1=extension_start, end1=end_date, is_half1=False, period1=None,
            start2=existing.start_date, end2=existing.end_date,
            is_half2=existing.is_half_day, period2=existing.half_day_period,
        ):
            raise ValueError(f"Extension conflicts with existing leave (#{existing.id}).")

    if substitute_user_id is not None:
        if substitute_user_id == user_id:
            raise ValueError("Applicant cannot nominate themselves as substitute.")
        substitute_conflict = LeaveRequest.objects.filter(
            user_id=substitute_user_id,
            status__in=active_statuses,
            start_date__lte=end_date,
            end_date__gte=extension_start,
        ).exists()
        if substitute_conflict:
            raise ValueError("Nominated substitute has overlapping pending or approved leave.")

    days = calculate_leave_days(
        category=original.category,
        start_date=extension_start,
        end_date=end_date,
    )
    balance = LeaveBalance.objects.select_for_update().filter(
        user_id=user_id,
        year=extension_start.year,
        category=original.category,
    ).first()
    available = balance.available_balance if balance else Decimal("0.00")
    if Decimal(str(days)) > available:
        raise ValueError(
            f"Insufficient {original.category} balance. Required: {days}, Available: {available}."
        )

    requires_substitute = substitute_user_id is not None
    status_value = (
        "extension_pending_substitute" if requires_substitute
        else "extension_pending_unit_head"
    )
    extension = LeaveRequest.objects.create(
        user_id=user_id,
        category=original.category,
        start_date=extension_start,
        end_date=end_date,
        days_calculated=Decimal(str(days)),
        reason=reason,
        status=status_value,
        substitute_user_id=substitute_user_id,
        substitute_status="pending" if requires_substitute else "none",
        unit_head_user_id=original.unit_head_user_id,
        is_extension=True,
        original_leave_id=original.id,
    )
    LeaveTransitionHistory.objects.create(
        leave_request=extension,
        from_status="draft",
        to_status=status_value,
        actor_user_id=user_id,
        remarks=f"Extension requested for leave #{original.id}.",
    )
    return extension
