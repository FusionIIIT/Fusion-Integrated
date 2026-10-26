"""Domain services and business logic for Employee Leave Management."""
from __future__ import annotations

import datetime

from django.core.exceptions import ValidationError
from django.db import transaction

from modules.elm.models import (
    LeaveApplication,
    LeaveBalance,
    LeavePolicy,
    SubstituteRequest,
)

DEFAULT_BALANCES = {
    "CL": 8,
    "RH": 2,
    "SCL": 15,
    "EL": 30,
    "VL": 15,
    "COL": 10,
}


def calculate_leave_days(start_date: datetime.date, end_date: datetime.date) -> int:
    if end_date < start_date:
        raise ValidationError("End date cannot be earlier than start date.")
    return (end_date - start_date).days + 1


def ensure_default_balances(user_id: int) -> list[LeaveBalance]:
    """Ensure standard initial leave balances exist for a user."""
    created = []
    for ltype, default_val in DEFAULT_BALANCES.items():
        policy = LeavePolicy.objects.filter(leave_type=ltype).first()
        days = policy.max_days if policy else default_val
        bal, _ = LeaveBalance.objects.get_or_create(
            user_id=user_id,
            leave_type=ltype,
            defaults={"balance": days},
        )
        created.append(bal)
    return created


@transaction.atomic
def apply_leave(
    *,
    user_id: int,
    leave_type: str,
    start_date: datetime.date,
    end_date: datetime.date,
    reason: str,
    station_leave: bool = False,
    substitute_user_id: int | None = None,
) -> LeaveApplication:
    """Submit a new leave application with validation."""
    days = calculate_leave_days(start_date, end_date)

    # Ensure balance record exists
    ensure_default_balances(user_id)
    balance_obj = LeaveBalance.objects.filter(
        user_id=user_id, leave_type=leave_type
    ).select_for_update().first()

    if not balance_obj or balance_obj.balance < days:
        available = balance_obj.balance if balance_obj else 0
        raise ValidationError(
            f"Insufficient leave balance for {leave_type}. "
            f"Requested {days} day(s), available: {available}."
        )

    application = LeaveApplication.objects.create(
        user_id=user_id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        station_leave=station_leave,
        substitute_user_id=substitute_user_id,
        status="PENDING",
    )

    if substitute_user_id:
        SubstituteRequest.objects.create(
            leave_application=application,
            substitute_user_id=substitute_user_id,
            status="PENDING",
        )

    return application


@transaction.atomic
def cancel_leave(*, application_id: int, user_id: int) -> LeaveApplication:
    """Cancel a pending leave application."""
    application = LeaveApplication.objects.select_for_update().get(id=application_id)
    if application.user_id != user_id:
        raise ValidationError("You can only cancel your own leave application.")
    if application.status != "PENDING":
        raise ValidationError(f"Cannot cancel application with status '{application.status}'.")

    application.status = "CANCELLED"
    application.save(update_fields=["status", "updated_at"])
    return application


@transaction.atomic
def review_leave(
    *,
    application_id: int,
    reviewer_user_id: int,
    action: str,
    remarks: str = "",
) -> LeaveApplication:
    """Approve or reject a pending leave application."""
    if action not in ("APPROVED", "REJECTED"):
        raise ValidationError(f"Invalid review action '{action}'. Must be APPROVED or REJECTED.")

    application = LeaveApplication.objects.select_for_update().get(id=application_id)
    if application.status != "PENDING":
        raise ValidationError(f"Application #{application_id} is already '{application.status}'.")

    if action == "APPROVED":
        days = calculate_leave_days(application.start_date, application.end_date)
        balance_obj = LeaveBalance.objects.filter(
            user_id=application.user_id,
            leave_type=application.leave_type,
        ).select_for_update().first()

        if balance_obj:
            if balance_obj.balance < days:
                raise ValidationError("Applicant balance is now insufficient to approve.")
            balance_obj.balance -= days
            balance_obj.save(update_fields=["balance", "updated_at"])

    application.status = action
    application.reviewed_by_user_id = reviewer_user_id
    application.review_remarks = remarks
    application.save(
        update_fields=[
            "status",
            "reviewed_by_user_id",
            "review_remarks",
            "updated_at",
        ]
    )
    return application


@transaction.atomic
def respond_to_substitute_request(
    *,
    substitute_request_id: int,
    substitute_user_id: int,
    accept: bool,
) -> SubstituteRequest:
    """Accept or decline a substitute request."""
    sub_req = SubstituteRequest.objects.select_for_update().get(id=substitute_request_id)
    if sub_req.substitute_user_id != substitute_user_id:
        raise ValidationError("You are not the designated substitute for this request.")
    if sub_req.status != "PENDING":
        raise ValidationError("This substitute request has already been processed.")

    sub_req.status = "ACCEPTED" if accept else "REJECTED"
    sub_req.save(update_fields=["status", "updated_at"])
    return sub_req
