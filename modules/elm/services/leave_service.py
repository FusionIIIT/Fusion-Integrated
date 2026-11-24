from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.elm.models import LeaveBalance, LeaveRequest, LeaveType


def calculate_leave_days(start_date, end_date, is_half_day: bool = False) -> Decimal:
    if end_date < start_date:
        raise BadRequestError(
            "End date cannot be earlier than start date.", code="invalid_date_range"
        )
    if is_half_day:
        if start_date != end_date:
            raise BadRequestError(
                "Half-day leave must be for a single date.", code="invalid_half_day"
            )
        return Decimal("0.5")
    days = (end_date - start_date).days + 1
    return Decimal(str(days))


@transaction.atomic
def submit_leave_request(
    *,
    employee_id: int,
    leave_type_id: int,
    start_date,
    end_date,
    is_half_day: bool = False,
    reason: str,
    contact_address: str = "",
    substitute_employee_id: int | None = None,
) -> LeaveRequest:
    try:
        leave_type = LeaveType.objects.get(id=leave_type_id, is_active=True)
    except LeaveType.DoesNotExist as exc:
        raise NotFoundError("Leave type not found.", code="leave_type_not_found") from exc

    total_days = calculate_leave_days(start_date, end_date, is_half_day)

    overlapping = LeaveRequest.objects.filter(
        employee_id=employee_id,
        status__in=["PENDING", "APPROVED"],
        start_date__lte=end_date,
        end_date__gte=start_date,
    ).exists()
    if overlapping:
        raise ConflictError(
            "Leave request overlaps with an existing active leave.", code="overlapping_leave"
        )

    balance, _ = LeaveBalance.objects.select_for_update().get_or_create(
        employee_id=employee_id,
        leave_type=leave_type,
        year=start_date.year,
        defaults={"total_allocated": leave_type.annual_quota, "used_days": Decimal("0.0")},
    )
    if balance.remaining_days < total_days:
        raise ConflictError(
            "Insufficient leave balance for this request.", code="insufficient_balance"
        )

    return LeaveRequest.objects.create(
        employee_id=employee_id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        total_days=total_days,
        is_half_day=is_half_day,
        reason=reason,
        contact_address=contact_address,
        substitute_employee_id=substitute_employee_id,
        status="PENDING",
    )


@transaction.atomic
def review_leave_request(
    *,
    reviewer_id: int,
    request_id: int,
    decision: str,
    review_comment: str = "",
) -> LeaveRequest:
    try:
        leave_req = (
            LeaveRequest.objects.select_for_update()
            .select_related("leave_type")
            .get(id=request_id)
        )
    except LeaveRequest.DoesNotExist as exc:
        raise NotFoundError("Leave request not found.", code="request_not_found") from exc

    if leave_req.status != "PENDING":
        raise ConflictError(
            "Only pending leave requests can be reviewed.", code="invalid_status"
        )

    if leave_req.employee_id == reviewer_id:
        raise PermissionDeniedError(
            "Employees cannot review their own leave request.", code="self_approval_forbidden"
        )

    if decision == "APPROVE":
        balance = LeaveBalance.objects.select_for_update().get(
            employee_id=leave_req.employee_id,
            leave_type=leave_req.leave_type,
            year=leave_req.start_date.year,
        )
        if balance.remaining_days < leave_req.total_days:
            raise ConflictError(
                "Insufficient leave balance to approve request.", code="insufficient_balance"
            )
        balance.used_days += leave_req.total_days
        balance.save(update_fields=["used_days", "updated_at"])
        leave_req.status = "APPROVED"
    elif decision == "REJECT":
        leave_req.status = "REJECTED"
    else:
        raise BadRequestError("Decision must be APPROVE or REJECT.", code="invalid_decision")

    leave_req.reviewer_id = reviewer_id
    leave_req.review_comment = review_comment
    leave_req.reviewed_at = timezone.now()
    leave_req.save(
        update_fields=["status", "reviewer_id", "review_comment", "reviewed_at", "updated_at"]
    )
    return leave_req


@transaction.atomic
def withdraw_leave_request(*, employee_id: int, request_id: int) -> LeaveRequest:
    try:
        leave_req = LeaveRequest.objects.select_for_update().get(id=request_id)
    except LeaveRequest.DoesNotExist as exc:
        raise NotFoundError("Leave request not found.", code="request_not_found") from exc

    if leave_req.employee_id != employee_id:
        raise PermissionDeniedError(
            "Cannot withdraw another employee's request.", code="forbidden"
        )

    if leave_req.status != "PENDING":
        raise ConflictError("Only pending requests can be withdrawn.", code="invalid_status")

    leave_req.status = "WITHDRAWN"
    leave_req.save(update_fields=["status", "updated_at"])
    return leave_req


@transaction.atomic
def cancel_approved_leave(*, employee_id: int, request_id: int) -> LeaveRequest:
    try:
        leave_req = (
            LeaveRequest.objects.select_for_update()
            .select_related("leave_type")
            .get(id=request_id)
        )
    except LeaveRequest.DoesNotExist as exc:
        raise NotFoundError("Leave request not found.", code="request_not_found") from exc

    if leave_req.employee_id != employee_id:
        raise PermissionDeniedError(
            "Cannot cancel another employee's request.", code="forbidden"
        )

    if leave_req.status != "APPROVED":
        raise ConflictError("Only approved requests can be cancelled.", code="invalid_status")

    balance = LeaveBalance.objects.select_for_update().get(
        employee_id=leave_req.employee_id,
        leave_type=leave_req.leave_type,
        year=leave_req.start_date.year,
    )
    balance.used_days = max(Decimal("0.0"), balance.used_days - leave_req.total_days)
    balance.save(update_fields=["used_days", "updated_at"])

    leave_req.status = "CANCELLED"
    leave_req.save(update_fields=["status", "updated_at"])
    return leave_req
