from datetime import date
from decimal import Decimal
from django.db import transaction

from modules.elm.domain.rules import calculate_leave_days, validate_leave_application
from modules.elm.models import (
    HolidayCalendar,
    LeaveActionHistory,
    LeaveBalance,
    LeaveRequest,
    LeaveStatus,
    LeaveType,
)
from modules.elm.selectors.leave import check_date_overlap, get_active_holidays, get_leave_balance


@transaction.atomic
def apply_leave(
    applicant_id: int,
    leave_type: str,
    start_date: date,
    end_date: date,
    purpose: str,
    is_half_day: bool = False,
    half_day_period: str | None = None,
    is_station_leave: bool = False,
    station_details: str | None = None,
    substitute_id: int | None = None,
) -> LeaveRequest:
    holidays = get_active_holidays(start_date.year)
    days = calculate_leave_days(
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        is_half_day=is_half_day,
        holidays=holidays,
    )

    has_overlap = check_date_overlap(applicant_id, start_date, end_date)
    balance_obj = get_leave_balance(applicant_id, leave_type, start_date.year)
    current_bal = float(balance_obj.balance) if balance_obj else 0.0

    is_valid, err_msg = validate_leave_application(
        leave_type=leave_type,
        days=days,
        current_balance=current_bal,
        has_overlap=has_overlap,
    )
    if not is_valid:
        raise ValueError(err_msg)

    sub_status = "PENDING" if substitute_id else "NOT_REQUIRED"
    init_status = LeaveStatus.PENDING_SUBSTITUTE if substitute_id else LeaveStatus.PENDING_APPROVAL

    req = LeaveRequest.objects.create(
        applicant_id=applicant_id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        is_half_day=is_half_day,
        half_day_period=half_day_period,
        purpose=purpose,
        is_station_leave=is_station_leave,
        station_details=station_details,
        substitute_id=substitute_id,
        substitute_status=sub_status,
        status=init_status,
    )

    LeaveActionHistory.objects.create(
        request=req,
        actor_id=applicant_id,
        action="SUBMITTED",
        comments=f"Applied for {days} day(s) of {leave_type}.",
    )
    return req


@transaction.atomic
def respond_substitute(request_id: int, substitute_id: int, accepted: bool, comments: str = "") -> LeaveRequest:
    req = LeaveRequest.objects.select_for_update().get(id=request_id)
    if req.substitute_id != substitute_id:
        raise PermissionError("Only the nominated substitute can respond.")
    if req.substitute_status != "PENDING":
        raise ValueError("Substitute response is not pending.")

    if accepted:
        req.substitute_status = "ACCEPTED"
        req.status = LeaveStatus.PENDING_APPROVAL
        action_name = "SUBSTITUTE_ACCEPTED"
    else:
        req.substitute_status = "DECLINED"
        req.status = LeaveStatus.PENDING_SUBSTITUTE
        action_name = "SUBSTITUTE_DECLINED"

    req.save(update_fields=["substitute_status", "status", "updated_at"])
    LeaveActionHistory.objects.create(
        request=req,
        actor_id=substitute_id,
        action=action_name,
        comments=comments,
    )
    return req


@transaction.atomic
def record_decision(
    request_id: int,
    actor_id: int,
    action: str,
    comments: str = "",
) -> LeaveRequest:
    req = LeaveRequest.objects.select_for_update().get(id=request_id)
    if req.status not in [LeaveStatus.PENDING_APPROVAL, LeaveStatus.RECOMMENDED]:
        raise ValueError(f"Cannot act on request in status {req.status}.")

    holidays = get_active_holidays(req.start_date.year)
    days = calculate_leave_days(
        leave_type=req.leave_type,
        start_date=req.start_date,
        end_date=req.end_date,
        is_half_day=req.is_half_day,
        holidays=holidays,
    )

    if action == "RECOMMEND":
        req.status = LeaveStatus.RECOMMENDED
    elif action == "NOT_RECOMMEND":
        req.status = LeaveStatus.NOT_RECOMMENDED
    elif action == "APPROVE":
        req.status = LeaveStatus.APPROVED
        # Deduct leave balance
        bal = LeaveBalance.objects.select_for_update().filter(
            employee_id=req.applicant_id,
            leave_type=req.leave_type,
            year=req.start_date.year,
        ).first()
        if bal:
            bal.availed += Decimal(str(days))
            bal.balance -= Decimal(str(days))
            bal.save(update_fields=["availed", "balance"])
    elif action == "REJECT":
        req.status = LeaveStatus.REJECTED
    else:
        raise ValueError(f"Unknown action {action}.")

    req.remarks = comments
    req.save(update_fields=["status", "remarks", "updated_at"])
    LeaveActionHistory.objects.create(
        request=req,
        actor_id=actor_id,
        action=action,
        comments=comments,
    )
    return req


@transaction.atomic
def withdraw_leave(request_id: int, applicant_id: int, reason: str = "") -> LeaveRequest:
    req = LeaveRequest.objects.select_for_update().get(id=request_id)
    if req.applicant_id != applicant_id:
        raise PermissionError("Only the applicant can withdraw this request.")
    if req.status in [LeaveStatus.APPROVED, LeaveStatus.REJECTED, LeaveStatus.WITHDRAWN, LeaveStatus.CANCELLED]:
        raise ValueError(f"Cannot withdraw request in status {req.status}.")

    req.status = LeaveStatus.WITHDRAWN
    req.save(update_fields=["status", "updated_at"])
    LeaveActionHistory.objects.create(
        request=req,
        actor_id=applicant_id,
        action="WITHDRAWN",
        comments=reason,
    )
    return req


@transaction.atomic
def cancel_leave(request_id: int, applicant_id: int, reason: str = "") -> LeaveRequest:
    req = LeaveRequest.objects.select_for_update().get(id=request_id)
    if req.applicant_id != applicant_id:
        raise PermissionError("Only the applicant can cancel this leave.")
    if req.status != LeaveStatus.APPROVED:
        raise ValueError("Only approved leaves can be cancelled.")
    if date.today() >= req.start_date:
        raise ValueError("Cannot cancel leave once start date has arrived; use resumption instead.")

    holidays = get_active_holidays(req.start_date.year)
    days = calculate_leave_days(
        leave_type=req.leave_type,
        start_date=req.start_date,
        end_date=req.end_date,
        is_half_day=req.is_half_day,
        holidays=holidays,
    )

    req.status = LeaveStatus.CANCELLED
    req.save(update_fields=["status", "updated_at"])

    # Restore balance
    bal = LeaveBalance.objects.select_for_update().filter(
        employee_id=req.applicant_id,
        leave_type=req.leave_type,
        year=req.start_date.year,
    ).first()
    if bal:
        bal.availed = max(Decimal("0.0"), bal.availed - Decimal(str(days)))
        bal.balance += Decimal(str(days))
        bal.save(update_fields=["availed", "balance"])

    LeaveActionHistory.objects.create(
        request=req,
        actor_id=applicant_id,
        action="CANCELLED",
        comments=reason,
    )
    return req
