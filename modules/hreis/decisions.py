from django.db import transaction
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from .models import EmployeeRecord, HRRequest, LeaveAccount, Notification
from .support import emit, require, route_for


def locked(request_id):
    try:
        employee_id = HRRequest.objects.values_list("employee_id", flat=True).get(pk=request_id)
    except HRRequest.DoesNotExist:
        raise NotFound("Request not found.") from None
    EmployeeRecord.objects.select_for_update().get(pk=employee_id)
    return HRRequest.objects.select_for_update().select_related("employee").get(pk=request_id)


@transaction.atomic
def verify(principal, request_id):
    req = locked(request_id)
    if req.kind not in ["LTC", "CPDA"] or req.status != "SUBMITTED":
        raise ValidationError("Invalid request type or status")
    require(principal, "hreis.claims.verify")
    if not req.documents or req.amount <= 0:
        raise ValidationError("Claim evidence and a positive amount are required.")
    route = route_for(req.employee, req.kind)
    req.route = route
    req.status = "PENDING"
    req.step = 0
    req.save(update_fields=["route", "status", "step", "updated_at"])
    emit(principal, "claim.verified", req.employee, req, {"request_id": request_id})
    return req


@transaction.atomic
def decide(principal, request_id, outcome, note=""):
    if outcome not in ("APPROVE", "REJECT", "FORWARD"):
        raise ValidationError("Unsupported decision.")
    req = locked(request_id)
    if req.status != "PENDING" or not req.route or req.step >= len(req.route):
        raise ValidationError("Invalid decision state")
    require(principal, "hreis.requests.decide")
    if principal.user_id != req.route[req.step]:
        raise PermissionDenied("Unauthorized to decide")
    if outcome == "REJECT":
        req.status = "REJECTED"
    elif outcome == "FORWARD":
        if req.step + 1 >= len(req.route):
            raise ValidationError("No further steps")
        req.step += 1
    elif outcome == "APPROVE":
        if req.step != len(req.route) - 1:
            raise ValidationError("Forward to the next authority.")
        req.status = "APPROVED"
        if req.kind == "LEAVE":
            try:
                account = LeaveAccount.objects.select_for_update().get(
                    employee=req.employee, policy=req.policy
                )
            except LeaveAccount.DoesNotExist:
                raise ValidationError("Leave account is missing.") from None
            if account.available < req.days:
                raise ValidationError("Insufficient leave balance")
            account.available -= req.days
            account.save(update_fields=["available"])
    req.save(update_fields=["status", "step", "updated_at"])
    emit(principal, outcome.lower(), req.employee, req, {"note": note, "step": req.step})
    if outcome == "FORWARD" and req.step < len(req.route):
        Notification.objects.create(
            recipient_id=req.route[req.step],
            request=req,
            event="forward",
            payload={"request_id": request_id},
        )
    return req


@transaction.atomic
def settle(principal, request_id, reference):
    req = locked(request_id)
    if req.kind not in ["LTC", "CPDA"] or req.status != "APPROVED":
        raise ValidationError("Invalid settlement state")
    require(principal, "hreis.claims.settle")
    reference = reference.strip()
    if not reference:
        raise ValidationError("An external settlement reference is required.")
    req.status = "SETTLED"
    req.save(update_fields=["status", "updated_at"])
    emit(principal, "claim.settled", req.employee, req, {"reference": reference})
    return req
