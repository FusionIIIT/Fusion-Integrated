"""Transactional leave-request operations."""

from django.db import transaction

from core.api.exceptions import ConflictError
from modules.elm.domain.leave_rules import (
    CONTINUOUS_DAY_CATEGORIES,
    SUPPORTED_CATEGORIES,
    count_leave_days,
)
from modules.elm.models import (
    LeaveAuditEvent,
    LeaveBalance,
    LeaveRequest,
    RestrictedHoliday,
)


@transaction.atomic
def submit_leave_request(
    *,
    employee_id: int,
    leave_category: str,
    start_date,
    end_date,
    reason: str,
    station_id: int | None = None,
    substitute_user_id: int | None = None,
) -> LeaveRequest:
    """Validate and submit a leave request."""
    if leave_category not in SUPPORTED_CATEGORIES:
        raise ConflictError("Unsupported leave category.", code="invalid_category")

    if end_date < start_date:
        raise ConflictError("End date cannot be before start date.", code="invalid_dates")

    if not (reason or "").strip():
        raise ConflictError("A reason for leave is required.", code="reason_required")

    if substitute_user_id == employee_id:
        raise ConflictError(
            "The applicant cannot be their own substitute.",
            code="invalid_substitute",
        )

    if leave_category == "RH":
        if start_date != end_date:
            raise ConflictError(
                "Restricted holiday requests must be for one date.",
                code="invalid_rh_dates",
            )

        holiday = RestrictedHoliday.objects.filter(
            date=start_date,
            is_published=True,
        )
        if station_id is not None:
            holiday = holiday.filter(station_id=station_id)

        if not holiday.exists():
            raise ConflictError(
                "No published restricted holiday exists for this date and station.",
                code="rh_not_available",
            )

    if leave_category in CONTINUOUS_DAY_CATEGORIES:
        requested_days = count_leave_days(start_date, end_date, leave_category)
        balance = LeaveBalance.objects.select_for_update().filter(
            employee_id=employee_id,
            leave_category=leave_category,
            year=start_date.year,
        ).first()

        if balance is None:
            raise ConflictError(
                "Leave balance is not configured for this employee and year.",
                code="balance_missing",
            )

        if balance.available_days < requested_days:
            raise ConflictError(
                "Insufficient leave balance.",
                code="insufficient_balance",
            )

    overlapping = LeaveRequest.objects.select_for_update().filter(
        employee_id=employee_id,
        status__in=[
            LeaveRequest.Status.PENDING,
            LeaveRequest.Status.APPROVED,
        ],
        start_date__lte=end_date,
        end_date__gte=start_date,
    )

    if overlapping.exists():
        raise ConflictError(
            "Leave overlaps an existing pending or approved request.",
            code="leave_overlap",
        )

    leave_request = LeaveRequest.objects.create(
        employee_id=employee_id,
        leave_category=leave_category,
        start_date=start_date,
        end_date=end_date,
        reason=reason.strip(),
        station_id=station_id,
        substitute_user_id=substitute_user_id,
        status=LeaveRequest.Status.PENDING,
        approval_stage=LeaveRequest.ApprovalStage.UNIT_HEAD,
    )
    LeaveAuditEvent.objects.create(
        leave_request=leave_request,
        actor_id=employee_id,
        action="SUBMITTED",
        details={"category": leave_category},
    )
    return leave_request
