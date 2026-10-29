"""Write operations and business workflows for Employee Leave Management.

All writes go through here, wrapped in atomic transactions with explicit locking.
"""
from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.domain.errors import ElmDomainError, InvalidDateRangeError, InvalidTransitionError
from modules.elm.domain.state_machine import (
    LeaveCategory,
    LeaveStatus,
    validate_dates,
    validate_transition,
)
from modules.elm.models import LeaveApplication


def apply_leave(
    *,
    principal,
    category: str,
    start_date: datetime.date,
    end_date: datetime.date,
    reason: str,
) -> LeaveApplication:
    """Submit a new leave application for the current user."""
    if not principal.has_permission("elm.leave_application.apply"):
        raise PermissionDeniedError("You do not have permission to apply for leave.")

    try:
        validate_dates(start_date, end_date)
    except InvalidDateRangeError as exc:
        raise BadRequestError(str(exc), code="invalid_date_range") from exc

    if category not in [c.value for c in LeaveCategory]:
        raise BadRequestError(f"Invalid leave category: '{category}'", code="invalid_category")

    if not reason.strip():
        raise BadRequestError("Reason cannot be empty.", code="blank_reason")

    # Guard: prevent overlapping pending or approved leave requests for the same applicant
    overlapping = LeaveApplication.objects.filter(
        user_id=principal.user_id,
        status__in=[LeaveStatus.PENDING.value, LeaveStatus.APPROVED.value],
        start_date__lte=end_date,
        end_date__gte=start_date,
    ).exists()
    if overlapping:
        raise ConflictError(
            "You already have a pending or approved leave application "
            "overlapping with these dates.",
            code="overlapping_leave",
        )

    with transaction.atomic():
        return LeaveApplication.objects.create(
            user_id=principal.user_id,
            category=category,
            start_date=start_date,
            end_date=end_date,
            reason=reason.strip(),
            status=LeaveStatus.PENDING.value,
        )


def review_leave(
    *,
    principal,
    application_id: int,
    action: str,
    remarks: str = "",
) -> LeaveApplication:
    """Approve or reject a leave application. Restricted to managers/HR."""
    if not principal.has_permission("elm.leave_application.manage"):
        raise PermissionDeniedError("Only authorized managers or HR can review leave applications.")

    target_status = {
        "approve": LeaveStatus.APPROVED.value,
        "reject": LeaveStatus.REJECTED.value,
    }.get(action.lower())

    if not target_status:
        raise BadRequestError(
            f"Invalid review action: '{action}'. Must be 'approve' or 'reject'.",
            code="invalid_action",
        )

    with transaction.atomic():
        try:
            app = LeaveApplication.objects.select_for_update().get(pk=application_id)
        except LeaveApplication.DoesNotExist as exc:
            raise NotFoundError(f"Leave application {application_id} not found.") from exc

        try:
            validate_transition(app.status, target_status)
        except InvalidTransitionError as exc:
            raise ConflictError(str(exc), code="invalid_transition") from exc

        app.status = target_status
        app.reviewed_by_user_id = principal.user_id
        app.reviewed_at = timezone.now()
        app.remarks = remarks.strip()
        app.save(update_fields=[
            "status",
            "reviewed_by_user_id",
            "reviewed_at",
            "remarks",
            "updated_at",
        ])

    return app


def cancel_leave(
    *,
    principal,
    application_id: int,
) -> LeaveApplication:
    """Cancel a pending leave application. Allowed for owner or managers."""
    with transaction.atomic():
        try:
            app = LeaveApplication.objects.select_for_update().get(pk=application_id)
        except LeaveApplication.DoesNotExist as exc:
            raise NotFoundError(f"Leave application {application_id} not found.") from exc

        is_owner = app.user_id == principal.user_id
        can_manage = principal.has_permission("elm.leave_application.manage")
        if not (is_owner or can_manage):
            raise PermissionDeniedError("You cannot cancel another user's leave application.")

        try:
            validate_transition(app.status, LeaveStatus.CANCELLED.value)
        except ElmDomainError as exc:
            raise ConflictError(str(exc), code="invalid_transition") from exc

        app.status = LeaveStatus.CANCELLED.value
        app.save(update_fields=["status", "updated_at"])

    return app
