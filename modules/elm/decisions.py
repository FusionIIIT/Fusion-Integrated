from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from modules.elm.checks import ensure_balance
from modules.elm.models import LeaveRequest
from modules.elm.validation import locked_employee
from modules.elm.workflows import emit, notify_task


def decision_request(pk, principal):
    try:
        req = LeaveRequest.objects.get(pk=pk)
    except LeaveRequest.DoesNotExist:
        raise ValidationError("Unknown pk") from None

    if not principal.has_permission("elm.leave_requests.approve"):
        raise PermissionDenied("Permission denied")

    locked_employee(req.employee)
    req = LeaveRequest.objects.select_for_update().get(pk=pk)

    if req.substitute_status not in ["NONE", "ACCEPTED"]:
        raise ValidationError("Invalid substitute status")

    if req.status != "PENDING":
        raise ValidationError("Status must be PENDING")

    if req.step >= len(req.route):
        raise PermissionDenied("Step out of bounds")

    if req.route[req.step] != principal.user_id:
        raise PermissionDenied("Route step mismatch")

    if principal.user_id == req.employee and req.route != [req.employee]:
        raise PermissionDenied("Route must be exactly [employee]")

    return req


def advance(req, principal, decision, notes=""):
    if req.step >= len(req.route) - 1:
        return False
    if req.step == 0:
        allowed_decisions = ["RECOMMEND", "NOT_RECOMMEND"]
    else:
        allowed_decisions = ["FORWARD", "RECOMMEND", "NOT_RECOMMEND"]

    if decision not in allowed_decisions:
        raise ValidationError("Invalid decision")

    if decision == "REJECT" and req.step != len(req.route) - 1:
        raise ValidationError("Intermediate REJECT is not allowed")

    emit(req, principal.user_id, decision, notes=notes, step=req.step)
    req.step += 1
    req.save()
    notify_task(req)
    return True


def approve(req, actor, notes=""):
    if req.operation == "RESUMPTION":
        from modules.elm.amendments import approve_resumption

        return approve_resumption(req, actor, notes)
    if req.operation == "CANCELLATION":
        from modules.elm.amendments import approve_cancellation

        return approve_cancellation(req, actor, notes)
    if req.operation not in ["LEAVE", "EXTENSION"]:
        raise ValidationError("Unsupported operation")
    if req.operation == "EXTENSION" and (
        not req.base_request or req.base_request.status != "APPROVED"
    ):
        raise ValidationError("Invalid base request for extension")
    row = ensure_balance(
        req.employee, req.leave_type, req.start_date, req.employee_kind, req.days, exclude=req.pk
    )
    row.balance -= req.days
    row.last_updated = timezone.now()
    row.save()
    req.status = "APPROVED"
    req.approved_at = timezone.now()
    req.save()
    emit(req, actor, "FINAL_APPROVED", delta=-req.days, recipient=req.employee, notes=notes)
    return req


@transaction.atomic
def decide(pk, principal, decision, notes=""):
    req = decision_request(pk, principal)
    if advance(req, principal, decision, notes):
        return req
    if decision not in ["APPROVE", "REJECT"]:
        raise ValidationError("Decision must be APPROVE or REJECT")
    if decision == "APPROVE":
        return approve(req, principal.user_id, notes)
    req.status = "REJECTED"
    req.save()
    emit(req, principal.user_id, "FINAL_REJECTED", recipient=req.employee, notes=notes)
    return req
