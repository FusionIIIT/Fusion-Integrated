
from datetime import date, datetime
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date

from .models import (
    EmployeeOfficeAssignment,
    LeaveBalance,
    LeaveRequest,
    LeaveType,
)


def _parse_leave_date(value):
    """Accept a date object or an ISO YYYY-MM-DD string."""
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        return parse_date(value)

    return None


def _calendar_days(start_date, end_date):
    """Return inclusive calendar-day count."""
    return Decimal((end_date - start_date).days + 1)



def apply_leave(
    user_id,
    leave_type_id,
    start_date_str,
    end_date_str,
    reason=None,
):
    """Create a pending leave request for an IAM employee ID."""
    start_date = _parse_leave_date(start_date_str)
    end_date = _parse_leave_date(end_date_str)

    if not start_date or not end_date:
        return {"error": "Invalid date format. Use YYYY-MM-DD."}

    if end_date < start_date:
        return {"error": "End date cannot be before start date."}

    # Find the employee's office from the admin-managed assignment.
    assignment = (
        EmployeeOfficeAssignment.objects
        .select_related("office")
        .filter(
            user_id=user_id,
            is_active=True,
            office__is_active=True,
        )
        .first()
    )

    if assignment is None:
        return {
            "error": (
                "No active office assignment exists for this employee. "
                "Please contact the administrator."
            )
        }

    try:
        leave_type = LeaveType.objects.get(pk=leave_type_id)
    except LeaveType.DoesNotExist:
        return {"error": "Leave type not found."}

    days_requested = _calendar_days(start_date, end_date)

    balance = LeaveBalance.objects.filter(
        user_id=user_id,
        leave_type=leave_type,
    ).first()

    if balance is None:
        return {"error": "No balance record exists for this leave type."}

    if balance.current_balance < days_requested:
        return {
            "error": (
                f"Insufficient balance. Available: "
                f"{balance.current_balance}; requested: {days_requested}."
            )
        }

    leave_request = LeaveRequest.objects.create(
        user_id=user_id,
        office=assignment.office,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        reason=reason or "",
        status="PENDING",
    )

    return {
        "id": leave_request.id,
        "status": leave_request.status,
        "message": "Leave request submitted successfully.",
    }

def process_leave_approval(request_id, approver_id):
    """Approve a pending request and deduct its balance exactly once.

    The caller must enforce the relevant IAM approval permission.
    """
    if not isinstance(approver_id, int) or approver_id <= 0:
        return {"error": "A valid IAM approver ID is required."}

    with transaction.atomic():
        try:
            leave_request = (
                LeaveRequest.objects
                .select_for_update()
                .select_related("leave_type")
                .get(pk=request_id)
            )
        except LeaveRequest.DoesNotExist:
            return {"error": "Leave request not found."}

        if leave_request.status != "PENDING":
            return {
                "error": (
                    "This request cannot be approved. "
                    f"Current status: {leave_request.status}."
                )
            }

        days_to_deduct = _calendar_days(
            leave_request.start_date,
            leave_request.end_date,
        )

        try:
            balance = (
                LeaveBalance.objects
                .select_for_update()
                .get(
                    user_id=leave_request.user_id,
                    leave_type=leave_request.leave_type,
                )
            )
        except LeaveBalance.DoesNotExist:
            return {"error": "No balance record exists for this leave type."}

        previous_balance = balance.current_balance

        if previous_balance < days_to_deduct:
            return {
                "error": (
                    f"Insufficient balance. Available: {previous_balance}; "
                    f"required: {days_to_deduct}."
                )
            }

        balance.current_balance = previous_balance - days_to_deduct
        balance.save(update_fields=["current_balance", "updated_at"])

        leave_request.status = "APPROVED"
        leave_request.approver_id = approver_id
        leave_request.approval_date = timezone.now()
        leave_request.save(
            update_fields=[
                "status",
                "approver_id",
                "approval_date",
                "updated_at",
            ]
        )

        return {
            "status": "success",
            "request_id": leave_request.pk,
            "message": (
                f"{leave_request.leave_type.name} leave approved. "
                "Balance deducted."
            ),
            "previous_balance": previous_balance,
            "current_balance": balance.current_balance,
        }


def process_leave_rejection(request_id, approver_id, reason=None):
    """Reject a pending request without deducting leave balance.

    The current LeaveRequest model has no rejection-reason field.
    The reason argument is accepted for compatibility but is not persisted.
    The caller must enforce the relevant IAM approval permission.
    """
    if not isinstance(approver_id, int) or approver_id <= 0:
        return {"error": "A valid IAM approver ID is required."}

    with transaction.atomic():
        try:
            leave_request = (
                LeaveRequest.objects
                .select_for_update()
                .get(pk=request_id)
            )
        except LeaveRequest.DoesNotExist:
            return {"error": "Leave request not found."}

        if leave_request.status != "PENDING":
            return {
                "error": (
                    "This request cannot be rejected. "
                    f"Current status: {leave_request.status}."
                )
            }

        leave_request.status = "REJECTED"
        leave_request.approver_id = approver_id
        leave_request.approval_date = timezone.now()
        leave_request.save(
            update_fields=[
                "status",
                "approver_id",
                "approval_date",
                "updated_at",
            ]
        )

        return {
            "status": "success",
            "request_id": leave_request.pk,
            "message": "Leave request rejected.",
        }
