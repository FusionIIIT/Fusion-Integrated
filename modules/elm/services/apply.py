"""Application creation service (EL-UC-001).

Enforces BR-EL-001 through BR-EL-015, BR-EL-020, BR-EL-030, BR-EL-031, BR-EL-036.
"""
from __future__ import annotations

import datetime
from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.domain.constants import HalfDayPeriod, LeaveCategory
from modules.elm.domain.counting import calculate_chargeable_days
from modules.elm.domain.eligibility import (
    ExistingLeaveSpan,
    check_applicant_overlap,
    check_category_eligibility,
    check_rh_calendar_applicability,
    check_station_leave_coupling,
    check_substitute_eligibility,
    check_vl_vacation_applicability,
)
from modules.elm.models import LeaveApplication, LeaveBalance, LeaveType
from modules.elm.selectors.applications import get_active_leaves_for_employee
from modules.elm.selectors.calendar import (
    get_academic_vacation_periods,
    get_closed_holiday_dates,
    get_published_rh_dates,
)
from modules.elm.services.audit import record_audit


def apply_for_leave(
    actor,
    leave_type_id: int,
    start_date: datetime.date,
    end_date: datetime.date,
    reason: str,
    is_half_day: bool = False,
    half_day_period: str = "NONE",
    is_station_leave: bool = False,
    station_destination: str = "",
    station_start_date: datetime.date | None = None,
    station_end_date: datetime.date | None = None,
    station_address: str = "",
    station_contact_no: str = "",
    substitute_id: int | None = None,
    is_faculty: bool = False,
    is_director: bool = False,
) -> LeaveApplication:
    """Validate and submit a new leave application (EL-UC-001)."""
    if actor is None or not getattr(actor, "is_authenticated", True):
        raise PermissionDeniedError("Authentication required.", code="unauthenticated")

    if hasattr(actor, "has_permission") and not actor.has_permission("leave_elm.application.apply"):
        raise PermissionDeniedError("This action needs leave_elm.application.apply.", code="permission_denied")

    user_id = getattr(actor, "user_id", None) or getattr(actor, "id", None)

    # 1. Fetch leave type
    try:
        leave_type = LeaveType.objects.get(id=leave_type_id, is_active=True)
    except LeaveType.DoesNotExist:
        raise NotFoundError("Leave type not found or inactive.", code="leave_type_not_found")

    # 2. Check category eligibility (BR-EL-001, BR-EL-006)
    elig_res = check_category_eligibility(leave_type.code, is_faculty=is_faculty)
    if not elig_res.is_valid:
        raise BadRequestError(elig_res.error_message, code=elig_res.error_code)

    # 3. Calculate chargeable leave days (BR-EL-010, BR-EL-011)
    closed_holidays = get_closed_holiday_dates(start_date.year)
    try:
        chargeable_days = calculate_chargeable_days(
            category=leave_type.code,
            start_date=start_date,
            end_date=end_date,
            is_half_day=is_half_day,
            half_day_period=half_day_period,
            closed_holidays=closed_holidays,
        )
    except ValueError as exc:
        raise BadRequestError(str(exc), code="invalid_dates") from exc

    # 4. RH calendar validation (BR-EL-003, BR-EL-031)
    if leave_type.code == LeaveCategory.RH.value:
        published_rh = get_published_rh_dates(start_date.year)
        rh_res = check_rh_calendar_applicability(start_date, published_rh)
        if not rh_res.is_valid:
            raise BadRequestError(rh_res.error_message, code=rh_res.error_code)

    # 5. VL vacation period validation (BR-EL-006)
    if leave_type.code == LeaveCategory.VL.value:
        vacation_periods = get_academic_vacation_periods(start_date.year)
        vl_res = check_vl_vacation_applicability(start_date, end_date, vacation_periods)
        if not vl_res.is_valid:
            raise BadRequestError(vl_res.error_message, code=vl_res.error_code)

    # 6. Station leave validation (BR-EL-013)
    station_res = check_station_leave_coupling(
        is_station_leave=is_station_leave,
        leave_start=start_date,
        leave_end=end_date,
        station_start=station_start_date,
        station_end=station_end_date,
        station_destination=station_destination,
    )
    if not station_res.is_valid:
        raise BadRequestError(station_res.error_message, code=station_res.error_code)

    # 7. Applicant non-overlap check (BR-EL-012)
    existing_leaves_qs = get_active_leaves_for_employee(user_id)
    existing_spans = [
        ExistingLeaveSpan(
            leave_id=el.id,
            category=el.leave_type.code,
            start_date=el.start_date,
            end_date=el.end_date,
            is_half_day=el.is_half_day,
            half_day_period=el.half_day_period,
        )
        for el in existing_leaves_qs
    ]
    overlap_res = check_applicant_overlap(
        category=leave_type.code,
        start_date=start_date,
        end_date=end_date,
        is_half_day=is_half_day,
        half_day_period=half_day_period,
        existing_leaves=existing_spans,
    )
    if not overlap_res.is_valid:
        raise ConflictError(overlap_res.error_message, code=overlap_res.error_code)

    # 8. Available balance check (BR-EL-002..009)
    try:
        balance = LeaveBalance.objects.get(employee_id=user_id, leave_type=leave_type, year=start_date.year)
    except LeaveBalance.DoesNotExist:
        raise NotFoundError("No leave balance configured for this leave type and year.", code="no_balance")

    available = float(balance.allotted - balance.used)
    if available < chargeable_days:
        raise ConflictError(
            f"Insufficient leave balance. Available: {available}, Requested: {chargeable_days}.",
            code="insufficient_balance",
        )

    # 9. Substitute eligibility check (BR-EL-014)
    if substitute_id is not None:
        sub_leaves_qs = get_active_leaves_for_employee(substitute_id)
        sub_spans = [
            ExistingLeaveSpan(
                leave_id=sl.id,
                category=sl.leave_type.code,
                start_date=sl.start_date,
                end_date=sl.end_date,
                is_half_day=sl.is_half_day,
                half_day_period=sl.half_day_period,
            )
            for sl in sub_leaves_qs
        ]
        sub_res = check_substitute_eligibility(
            applicant_id=user_id,
            substitute_id=substitute_id,
            start_date=start_date,
            end_date=end_date,
            substitute_active_leaves=sub_spans,
            is_employee=True,
        )
        if not sub_res.is_valid:
            raise BadRequestError(sub_res.error_message, code=sub_res.error_code)

    # 10. Determine initial status and stage (BW-EL-01..09, CW-EL-01)
    if substitute_id is not None:
        initial_status = "AWAITING_SUBSTITUTE"
        sub_status = "PENDING"
    elif is_director:
        initial_status = "AWAITING_DIRECTOR_SELF_SANCTION"
        sub_status = "NONE"
    else:
        initial_status = "AWAITING_UNIT_HEAD"
        sub_status = "NONE"

    with transaction.atomic():
        application = LeaveApplication.objects.create(
            employee_id=user_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            is_half_day=is_half_day,
            half_day_period=half_day_period,
            days=chargeable_days,
            reason=reason,
            status=initial_status,
            is_station_leave=is_station_leave,
            station_destination=station_destination,
            station_start_date=station_start_date,
            station_end_date=station_end_date,
            station_address=station_address,
            station_contact_no=station_contact_no,
            substitute_id=substitute_id,
            substitute_status=sub_status,
        )
        record_audit(
            application=application,
            actor_id=user_id,
            action="APPLY",
            from_status="DRAFT",
            to_status=initial_status,
            remarks=reason,
        )

    return application
