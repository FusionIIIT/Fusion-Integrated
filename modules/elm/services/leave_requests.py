"""All writes for leave requests in ELM.

Transactional choke point for state changes, leave balance deduction,
and self-approval guards.
"""
from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.domain.state_machine import (
    InvalidTransitionError,
    calculate_leave_days,
    validate_transition,
)
from modules.elm.models import LeaveBalance, LeaveRequest, LeaveType


def apply_leave(
    principal,
    leave_type: LeaveType,
    start_date: datetime.date,
    end_date: datetime.date,
    reason: str,
) -> LeaveRequest:
    if principal is None:
        raise PermissionDeniedError("Authentication required.")
    if not principal.has_permission("elm.leave_request.create"):
        raise PermissionDeniedError("You do not have permission to apply for leave.")
    if start_date > end_date:
        raise BadRequestError("Start date cannot be after end date.")

    requested_days = calculate_leave_days(start_date, end_date)

    with transaction.atomic():
        overlapping = LeaveRequest.objects.filter(
            employee_user_id=principal.user_id,
            status__in=["pending", "approved"],
            start_date__lte=end_date,
            end_date__gte=start_date,
        ).exists()
        if overlapping:
            raise ConflictError("An overlapping leave request already exists.")

        # Minimal spec rule: create-on-first-apply from LeaveType.max_days_per_year under lock
        balance, _ = LeaveBalance.objects.select_for_update().get_or_create(
            user_id=principal.user_id,
            leave_type=leave_type,
            year=start_date.year,
            defaults={"total_days": leave_type.max_days_per_year, "used_days": 0},
        )
        if balance.remaining_days < requested_days:
            raise ConflictError(
                f"Insufficient leave balance: requested {requested_days} days, "
                f"but only {balance.remaining_days} remaining."
            )

        return LeaveRequest.objects.create(
            employee_user_id=principal.user_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            status="pending",
        )


def review_leave(
    principal,
    leave_request_id: int,
    action: str,
    remarks: str = "",
) -> LeaveRequest:
    if principal is None:
        raise PermissionDeniedError("Authentication required.")
    if not principal.has_permission("elm.leave_request.review"):
        raise PermissionDeniedError("You do not have permission to review leave requests.")

    target_status = "approved" if action == "approve" else "rejected"

    with transaction.atomic():
        try:
            leave = LeaveRequest.objects.select_for_update().get(id=leave_request_id)
        except LeaveRequest.DoesNotExist as err:
            raise NotFoundError(f"Leave request {leave_request_id} not found.") from err

        # Self-approval guard: employee cannot approve or reject their own leave
        if leave.employee_user_id == principal.user_id:
            raise PermissionDeniedError("Submitter cannot review their own leave request.")

        try:
            validate_transition(leave.status, target_status)
        except InvalidTransitionError as err:
            raise ConflictError(str(err)) from err

        if target_status == "approved":
            days = calculate_leave_days(leave.start_date, leave.end_date)
            balance = (
                LeaveBalance.objects.select_for_update()
                .filter(
                    user_id=leave.employee_user_id,
                    leave_type=leave.leave_type,
                    year=leave.start_date.year,
                )
                .first()
            )
            if balance is None:
                balance = LeaveBalance.objects.create(
                    user_id=leave.employee_user_id,
                    leave_type=leave.leave_type,
                    year=leave.start_date.year,
                    total_days=leave.leave_type.max_days_per_year,
                    used_days=0,
                )
            if balance.remaining_days < days:
                raise ConflictError(
                    f"Insufficient leave balance: {balance.remaining_days} days remaining, "
                    f"but {days} required."
                )
            balance.used_days += days
            balance.save(update_fields=["used_days", "updated_at"])

        leave.status = target_status
        leave.reviewed_by_user_id = principal.user_id
        leave.reviewed_at = timezone.now()
        leave.remarks = remarks
        leave.save(
            update_fields=[
                "status",
                "reviewed_by_user_id",
                "reviewed_at",
                "remarks",
                "updated_at",
            ]
        )

        return leave
