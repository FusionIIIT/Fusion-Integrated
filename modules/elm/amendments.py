from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from modules.elm.application import validate_request
from modules.elm.models import LeaveRequest
from modules.elm.validation import account, count_days, resolve_route
from modules.elm.workflows import emit, get_request, notify_task


def amendment_base(pk, principal):
    base = get_request(pk)
    if base.employee != principal.user_id:
        raise PermissionDenied("User does not have permission to amend this request.")
    if base.operation != "LEAVE" or base.status != "APPROVED":
        raise ValidationError(
            "Request must be of type 'LEAVE' and status 'APPROVED' for amendment."
        )
    if LeaveRequest.objects.filter(base_request=base, status="PENDING").exists():
        raise ValidationError("Only one pending amendment is allowed for this request.")
    return base


def new_child(base, operation, **overrides):
    attrs = {
        "employee": base.employee,
        "employee_kind": base.employee_kind,
        "unit": base.unit,
        "leave_type": base.leave_type,
        "start_date": base.start_date,
        "end_date": base.end_date,
        "purpose": base.purpose,
        "half_day": base.half_day,
        "station_leave": base.station_leave,
        "station_details": base.station_details,
        "medical_evidence": base.medical_evidence,
        "days": base.days,
        "operation": operation,
        "base_request": base,
        "status": "PENDING",
        "substitute": None,
        "substitute_status": "NONE",
        "step": 0,
        "route": resolve_route(base.employee, base.leave_type.type),
    }
    attrs.update(overrides)
    return LeaveRequest.objects.create(**attrs)


@transaction.atomic
def cancel_request(pk, principal):
    base = amendment_base(pk, principal)
    if timezone.localdate() >= base.start_date:
        raise ValidationError("Pre-start cancellation is unavailable.")
    child = new_child(base, "CANCELLATION")
    emit(child, principal.user_id, "CANCELLATION_REQUESTED")
    notify_task(child)
    return child


def approve_cancellation(req, actor, notes=""):
    base = get_request(req.base_request_id)
    if base.status != "APPROVED" or timezone.localdate() >= base.start_date:
        raise ValidationError("Base request must be approved and start date in the future.")
    if base.amendments.filter(operation="EXTENSION", status="APPROVED").exists():
        raise ValidationError("Cannot cancel a request with approved extensions.")
    row = account(base.employee, base.leave_type, base.start_date.year, base.employee_kind)
    row.balance += base.days
    row.last_updated = timezone.now()
    row.save()
    base.status = "CANCELLED"
    base.save()
    req.status = "APPROVED"
    req.approved_at = timezone.now()
    req.save()
    emit(req, actor, "CANCELLATION_APPROVED", delta=base.days, recipient=req.employee, notes=notes)
    return req


def approved_end(base):
    queryset = base.amendments.filter(operation="EXTENSION", status="APPROVED")
    dates = list(queryset.values_list("end_date", flat=True))
    dates.append(base.end_date)
    return max(dates)


@transaction.atomic
def extension_request(pk, principal, end_date, data=None):
    base = amendment_base(pk, principal)
    if base.actual_return_date is not None:
        raise ValidationError("Leave has already resumed")
    if base.leave_type.type not in ["EL", "COL", "VL"]:
        raise ValidationError("Only EL, COL, VL may extend")
    approved_end_date = approved_end(base)
    if not (base.start_date <= timezone.localtime().date() <= approved_end_date):
        raise ValidationError("Request date out of range")
    if end_date <= approved_end_date:
        raise ValidationError("End date must be after approved end date")
    params = {
        "leave_type": base.leave_type,
        "start_date": approved_end_date + timedelta(days=1),
        "end_date": end_date,
        "purpose": base.purpose,
        "half_day": "FULL",
        "substitute": base.substitute,
        "station_leave": base.station_leave,
        "station_details": base.station_details,
        "medical_evidence": base.medical_evidence,
    }
    if data:
        params.update(
            {
                "purpose": data.get("purpose", params["purpose"]),
                "substitute": data.get("substitute", params["substitute"]),
                "station_leave": data.get("station_leave", params["station_leave"]),
                "station_details": data.get("station_details", params["station_details"]),
                "medical_evidence": data.get("medical_evidence", params["medical_evidence"]),
            }
        )
    attrs = validate_request(params, base.employee, base.employee_kind, exclude=base.pk)
    attrs.update({"operation": "EXTENSION", "base_request": base})
    leave_request = LeaveRequest.objects.create(**attrs)
    emit(leave_request, principal.user_id, "EXTENSION_REQUESTED")
    notify_task(leave_request)
    return leave_request


def resumption_request(pk, principal, actual_return_date, notes=""):
    @transaction.atomic
    def _resumption_request(pk, principal, actual_return_date, notes):
        base = amendment_base(pk, principal)
        if base.leave_type.type not in ["EL", "COL", "VL"]:
            raise ValidationError("Invalid leave type for resumption")
        if not (base.start_date <= actual_return_date <= timezone.localdate()):
            raise ValidationError("Actual return date must be between start date and today")
        if not notes.strip():
            raise ValidationError("Resumption details required")
        if base.amendments.filter(operation="RESUMPTION", status="APPROVED").exists():
            raise ValidationError("Resumption already approved")
        route = resolve_route(base.employee, base.leave_type.type)
        child = new_child(
            base,
            "RESUMPTION",
            actual_return_date=actual_return_date,
            notes=notes.strip(),
            route=[route[-1]],
        )
        emit(child, principal.user_id, "RESUMPTION_SUBMITTED")
        notify_task(child)
        return child

    return _resumption_request(pk, principal, actual_return_date, notes)


def approve_resumption(req, actor, notes=""):
    base = get_request(req.base_request_id)
    if base.status != "APPROVED" or base.leave_type.type not in ("EL", "COL", "VL"):
        raise ValidationError("Base request must be approved with valid leave type")
    if (
        not req.actual_return_date
        or req.actual_return_date < base.start_date
        or req.actual_return_date > timezone.localtime().date()
    ):
        raise ValidationError("Actual return date must be between start date and today")
    if base.amendments.filter(operation="RESUMPTION", status="APPROVED").exists():
        raise ValidationError("Resumption already approved for base request")

    charged = base.days + sum(
        base.amendments.filter(operation="EXTENSION", status="APPROVED").values_list(
            "days", flat=True
        ),
        Decimal("0"),
    )
    from modules.elm.checks import ensure_overlap_free

    if req.actual_return_date > approved_end(base):
        ensure_overlap_free(
            base.employee,
            base.leave_type,
            approved_end(base) + timedelta(days=1),
            req.actual_return_date,
            "FULL",
            exclude=base.pk,
        )
    actual = count_days(base.leave_type.type, base.start_date, req.actual_return_date, "FULL")
    delta = charged - actual

    row = account(base.employee, base.leave_type, base.start_date.year, base.employee_kind)
    if row.balance + delta < 0:
        raise ValidationError("Insufficient balance for resumption")
    row.balance += delta
    row.last_updated = timezone.now()
    row.save()

    base.actual_return_date = req.actual_return_date
    base.save()

    req.status = "APPROVED"
    req.approved_at = timezone.now()
    req.save()

    emit(
        req,
        actor,
        "RESUMPTION_REVIEWED",
        delta=delta,
        recipient=req.employee,
        actual_start=base.start_date.isoformat(),
        actual_end=req.actual_return_date.isoformat(),
        approved_end=approved_end(base).isoformat(),
        notes=notes,
    )
    if delta != 0:
        emit(
            req,
            actor,
            "ATTENDANCE_SYNC_REQUIRED",
            actual_start=base.start_date.isoformat(),
            actual_end=req.actual_return_date.isoformat(),
        )

    return req
