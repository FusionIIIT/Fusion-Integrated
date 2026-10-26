"""Ongoing leave extension workflow (CW-EL-03, EL-UC-009)."""

from datetime import date, timedelta

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.leave.domain.counting import calculate_leave_days
from modules.leave.domain.entities import LeaveStatus
from modules.leave.domain.errors import DomainError
from modules.leave.domain.rules import (
    validate_balance_sufficient,
    validate_extension_allowed,
)
from modules.leave.models import LeaveActionLog, LeaveApplication, LeaveBalance


def request_extension(
    parent_application_id: int,
    principal,
    new_end_date: date,
    reason: str,
    substitute_user_id: int | None = None,
) -> LeaveApplication:
    """Request extension of ongoing EL, COL, or VL (EL-UC-009)."""
    with transaction.atomic():
        try:
            parent = LeaveApplication.objects.select_for_update().get(pk=parent_application_id)
        except LeaveApplication.DoesNotExist:
            raise NotFoundError(f"Application #{parent_application_id} not found.") from None

        if parent.applicant_user_id != principal.user_id:
            raise ConflictError("You can only request extension for your own leave.")

        try:
            validate_extension_allowed(
                leave_status=parent.status,
                category=parent.leave_type,
                start_date=parent.start_date,
                end_date=parent.end_date,
                today=date.today(),
            )
        except DomainError as e:
            raise ConflictError(e.message) from None

        if new_end_date <= parent.end_date:
            raise ConflictError(
                f"New end date {new_end_date} must be after current end date {parent.end_date}."
            )

        # Incremental period is from parent.end_date + 1 to new_end_date
        inc_start = parent.end_date + timedelta(days=1)
        inc_days = calculate_leave_days(
            category=parent.leave_type,
            start_date=inc_start,
            end_date=new_end_date,
        )

        bal = LeaveBalance.objects.select_for_update().get(
            user_id=principal.user_id,
            year=inc_start.year,
            leave_type=parent.leave_type,
        )
        try:
            validate_balance_sufficient(inc_days, bal.balance)
        except DomainError as e:
            raise ConflictError(e.message) from None

        sub_id = substitute_user_id or parent.substitute_user_id
        initial_status = (
            LeaveStatus.AWAITING_SUBSTITUTE.value
            if sub_id
            else LeaveStatus.AWAITING_UNIT_HEAD.value
        )

        ext_app = LeaveApplication.objects.create(
            applicant_user_id=principal.user_id,
            leave_type=parent.leave_type,
            start_date=inc_start,
            end_date=new_end_date,
            days_count=inc_days,
            reason=f"Extension of Leave #{parent.pk}: {reason}",
            status=initial_status,
            substitute_user_id=sub_id,
            substitute_status="PENDING" if sub_id else "ACCEPTED",
            parent_leave_id=parent.pk,
        )

        LeaveActionLog.objects.create(
            application=ext_app,
            actor_user_id=principal.user_id,
            action="REQUEST_EXTENSION",
            from_status="DRAFT",
            to_status=initial_status,
            remarks=f"Incremental {inc_days} days extension requested",
        )

        return ext_app
