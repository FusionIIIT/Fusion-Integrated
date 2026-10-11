from datetime import date

from django.db import transaction
from django.core.exceptions import ValidationError

from modules.elm.models import LeaveRequest


PENDING_STATUSES = {
    "pending",
    "pending_substitute",
    "pending_unit_head",
    "pending_establishment",
    "pending_sanction",
}


@transaction.atomic
def decide_request(*, request_id, actor, decision, today=None):
    """Approve or reject a request that is awaiting a decision."""
    leave = LeaveRequest.objects.select_for_update().get(pk=request_id)

    if leave.status not in PENDING_STATUSES:
        raise ValidationError("This request is not awaiting approval.")

    if decision not in {"approve", "reject"}:
        raise ValidationError("Decision must be approve or reject.")

    leave.status = (
        LeaveRequest.Status.APPROVED
        if decision == "approve"
        else LeaveRequest.Status.REJECTED
    )
    leave.save(update_fields=["status", "updated_at"])
    return leave


@transaction.atomic
def withdraw_request(*, request_id, employee):
    """Employees may withdraw their own pending requests."""
    leave = LeaveRequest.objects.select_for_update().get(
        pk=request_id, employee=employee
    )

    if leave.status not in PENDING_STATUSES:
        raise ValidationError("Only pending requests can be withdrawn.")

    leave.status = LeaveRequest.Status.WITHDRAWN
    leave.save(update_fields=["status", "updated_at"])
    return leave


@transaction.atomic
def cancel_approved_request(*, request_id, employee, today=None):
    """Cancellation is allowed only before the approved leave starts."""
    today = today or date.today()
    leave = LeaveRequest.objects.select_for_update().get(
        pk=request_id, employee=employee
    )

    if leave.status != LeaveRequest.Status.APPROVED:
        raise ValidationError("Only approved leave can be cancelled.")

    if today >= leave.start_date:
        raise ValidationError("Approved leave cannot be cancelled on or after its start date.")

    leave.status = LeaveRequest.Status.CANCELLED
    leave.save(update_fields=["status", "updated_at"])
    return leave
