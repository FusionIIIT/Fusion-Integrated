from decimal import Decimal

from django.db import transaction
from django.db.transaction import atomic
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError

from modules.elm.application import validate_request
from modules.elm.checks import ensure_nominee
from modules.elm.models import LeaveEvent, LeaveRequest
from modules.elm.validation import locked_employee


def emit(req, actor, action, delta=Decimal("0"), **details):
    return LeaveEvent.objects.create(
        request=req, employee=req.employee, actor=actor, action=action, delta=delta, details=details
    )


def notify_task(req):
    if req.status != "PENDING":
        return
    if req.substitute_status == "DECLINED":
        return
    if req.substitute_status == "PENDING":
        recipient = req.substitute
    else:
        if req.step < len(req.route):
            recipient = req.route[req.step]
        else:
            raise DRFValidationError("Invalid step index")
    if not recipient:
        raise DRFValidationError("Recipient not found")
    emit(req, None, "TASK_ASSIGNED", recipient=recipient, step=req.step)


@transaction.atomic
def submit(data, principal):
    if principal.kind not in ["faculty", "staff"]:
        raise ValidationError("Invalid principal kind")
    locked_employee(principal.user_id)
    attrs = validate_request(data, principal.user_id, principal.kind)
    req = LeaveRequest.objects.create(**attrs)
    emit(req, principal.user_id, "SUBMITTED")
    notify_task(req)
    return req


@atomic
def withdraw(pk, principal):
    locked_employee(principal.user_id)
    try:
        req = LeaveRequest.objects.select_for_update().get(pk=pk)
    except LeaveRequest.DoesNotExist:
        raise NotFound() from None
    if req.employee != principal.user_id:
        raise PermissionDenied()
    if req.status != "PENDING":
        raise ValidationError()
    req.status = "WITHDRAWN"
    req.save()
    emit(
        req,
        actor=principal.user_id,
        action="WITHDRAWN",
        delta=Decimal("0"),
        recipients=[req.employee]
        + req.route
        + ([req.substitute] if req.substitute is not None else []),
    )
    return req


@transaction.atomic
def substitute_response(pk, principal, accept):
    if not isinstance(accept, bool):
        raise ValidationError("Accept must be a boolean.")
    req = get_request(pk)
    if req.status != "PENDING" or req.substitute_status != "PENDING":
        raise ValidationError("Request status or substitute status is not PENDING.")
    if req.substitute != principal.user_id:
        raise PermissionDenied("User is not authorized to respond to this request.")
    if accept:
        if not ensure_nominee(req.employee, req.substitute, True, req.start_date, req.end_date):
            raise ValidationError("Nominee is not eligible for the substitute request.")
        req.substitute_status = "ACCEPTED"
    else:
        req.substitute_status = "DECLINED"
    req.save()
    emit(
        req,
        principal.user_id,
        "SUBSTITUTE_ACCEPTED" if accept else "SUBSTITUTE_DECLINED",
        recipient=req.employee,
    )
    if accept:
        notify_task(req)
    return req


@transaction.atomic
def renominate(pk, principal, substitute):
    req = get_request(pk)
    if req.employee != principal.user_id:
        raise PermissionDenied
    if req.status != "PENDING" or req.substitute_status != "DECLINED":
        raise ValidationError
    if req.substitute == substitute:
        raise ValidationError
    if not ensure_nominee(req.employee, substitute, True, req.start_date, req.end_date):
        raise ValidationError
    req.substitute = substitute
    req.substitute_status = "PENDING"
    req.save()
    emit(req, principal.user_id, "RENOMINATED", recipient=substitute)
    notify_task(req)
    return req


def get_request(pk):
    try:
        req = LeaveRequest.objects.get(pk=pk)
        locked_employee(req.employee)
        return LeaveRequest.objects.select_for_update().get(pk=pk)
    except LeaveRequest.DoesNotExist:
        raise NotFound("Leave request not found") from None
