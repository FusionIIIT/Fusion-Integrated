from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from modules.hreis.domain.policy import HRPolicy
from modules.hreis.models import (
    Appraisal,
    AppraisalWindow,
    AuditEntry,
    Claim,
    EmployeeRecord,
    LeaveRequest,
    Notification,
    WorkflowRoute,
)


def record_event(obj, action, principal, detail=None):
    AuditEntry.objects.create(
        entity_type=type(obj).__name__,
        entity_id=obj.pk,
        action=action,
        actor_id=principal.user_id,
        detail=detail or {},
    )


def notify(user_id, kind, message):
    return Notification.objects.create(user_id=user_id, kind=kind, message=message)


def route_for(record, request_kind):
    route = WorkflowRoute.objects.filter(
        category=record.category, request_kind=request_kind
    ).first()
    if route is None or not isinstance(route.authorities, list) or not route.authorities:
        raise ValidationError(
            {
                "workflow": (
                    "HR administrator must configure the approval route "
                    "for this category and request type."
                )
            }
        )
    return route.authorities


def current_authority(record, kind, step, frozen_roles=None):
    authorities = frozen_roles if frozen_roles is not None else route_for(record, kind)
    if step >= len(authorities):
        raise ValidationError({"workflow": "Approval workflow has no current authority."})
    return authorities[step], authorities


def check_authority(principal, expected):
    if principal.active_role != expected:
        raise PermissionDenied(
            "Only the configured current approval authority may decide this request."
        )


@transaction.atomic
def save_record(data, principal, user_id=None):
    if user_id is None:
        if EmployeeRecord.objects.filter(user_id=data["user_id"]).exists():
            raise ValidationError({"user_id": "Service record already exists."})
        record = EmployeeRecord.objects.create(**data)
        action = "created"
    else:
        try:
            record = EmployeeRecord.objects.select_for_update().get(user_id=user_id)
        except EmployeeRecord.DoesNotExist as exc:
            raise ValidationError({"record": "Service record not found."}) from exc
        for key, value in data.items():
            if key == "user_id":
                continue
            setattr(record, key, value)
        record.save()
        action = "updated"
    record_event(record, action, principal)
    return record


@transaction.atomic
def submit_leave(record, fields, principal):
    record = EmployeeRecord.objects.select_for_update().get(pk=record.pk)
    approval_roles = route_for(record, "leave")
    leave_type = fields["leave_type"]
    days = Decimal(fields["days"])
    try:
        HRPolicy.available_leave(record.leave_balances, leave_type, days)
    except ValueError as exc:
        raise ValidationError({"days": str(exc)}) from exc
    leave = LeaveRequest.objects.create(record=record, approval_roles=approval_roles, **fields)
    record_event(leave, "submitted", principal)
    notify(record.user_id, "leave", "Leave request submitted for approval.")
    return leave


@transaction.atomic
def decide_leave(pk, outcome, principal):
    leave = LeaveRequest.objects.select_for_update().select_related("record").get(pk=pk)
    if leave.status != "pending":
        raise ValidationError({"status": "Request is already decided."})
    role, route = current_authority(leave.record, "leave", leave.current_step, leave.approval_roles)
    check_authority(principal, role)
    if outcome == "forward":
        if leave.current_step + 1 >= len(route):
            raise ValidationError({"outcome": "No next authority to forward to."})
        leave.current_step += 1
    elif outcome == "reject":
        leave.status = "rejected"
    elif outcome == "approve":
        record = EmployeeRecord.objects.select_for_update().get(pk=leave.record_id)
        try:
            remaining = HRPolicy.available_leave(
                record.leave_balances, leave.leave_type, leave.days
            )
        except ValueError as exc:
            raise ValidationError({"balance": str(exc)}) from exc
        record.leave_balances = {**record.leave_balances, leave.leave_type: str(remaining)}
        record.save(update_fields=["leave_balances", "updated_at"])
        leave.status = "approved"
    else:
        raise ValidationError({"outcome": "Choose approve, reject, or forward."})
    leave.save(update_fields=["status", "current_step", "updated_at"])
    record_event(leave, outcome, principal, {"step": leave.current_step})
    notify(leave.record.user_id, "leave", f"Leave request {outcome}.")
    return leave


@transaction.atomic
def submit_appraisal(record, fields, principal):
    now = timezone.now()
    window = AppraisalWindow.objects.filter(year=fields["year"]).first()
    if not window or not (window.opens_at <= now <= window.closes_at):
        raise ValidationError({"year": "Appraisal submissions are not open for this year."})
    if Appraisal.objects.filter(record=record, year=fields["year"]).exists():
        raise ValidationError({"year": "An appraisal has already been submitted for this year."})
    appraisal = Appraisal.objects.create(
        record=record, year=fields["year"], content=fields["content"]
    )
    record_event(appraisal, "submitted", principal)
    notify(record.user_id, "appraisal", "Yearly appraisal submitted.")
    return appraisal


@transaction.atomic
def assign_appraisal(pk, roles, principal):
    obj = Appraisal.objects.select_for_update().get(pk=pk)
    if obj.status != "submitted":
        raise ValidationError({"status": "Only submitted appraisals may be assigned."})
    if (
        not isinstance(roles, list)
        or not roles
        or any(x not in ("HOD", "Registrar", "Director") for x in roles)
        or len(roles) != len(set(roles))
    ):
        raise ValidationError(
            {
                "reviewer_roles": (
                    "Provide an ordered, non-repeating set of HOD, Registrar, or Director roles."
                )
            }
        )
    obj.reviewer_roles = roles
    obj.status = "review"
    obj.save(update_fields=["reviewer_roles", "status"])
    record_event(obj, "reviewers_assigned", principal, {"reviewer_roles": roles})
    notify(obj.record.user_id, "appraisal", "Appraisal reviewers assigned.")
    return obj


@transaction.atomic
def review_appraisal(pk, principal):
    obj = Appraisal.objects.select_for_update().get(pk=pk)
    if obj.status != "review" or obj.current_step >= len(obj.reviewer_roles):
        raise ValidationError({"status": "Appraisal is not pending review."})
    check_authority(principal, obj.reviewer_roles[obj.current_step])
    obj.current_step += 1
    if obj.current_step >= len(obj.reviewer_roles):
        obj.status = "closed"
        obj.closed_at = timezone.now()
    obj.save(update_fields=["current_step", "status", "closed_at"])
    record_event(obj, "finalized" if obj.status == "closed" else "review_forwarded", principal)
    notify(obj.record.user_id, "appraisal", f"Appraisal {obj.status}.")
    return obj


@transaction.atomic
def submit_claim(record, fields, principal):
    approval_roles = route_for(record, fields["kind"])
    if not HRPolicy.valid_claim_documents(fields.get("documents")):
        raise ValidationError({"documents": "Supporting documents are required."})
    obj = Claim.objects.create(record=record, approval_roles=approval_roles, **fields)
    record_event(obj, "submitted", principal)
    notify(record.user_id, "claim", f"{obj.kind.upper()} request submitted.")
    return obj


@transaction.atomic
def verify_claim(pk, principal, documents_verified, eligible):
    obj = Claim.objects.select_for_update().select_related("record").get(pk=pk)
    if obj.status != "awaiting_hr":
        raise ValidationError({"status": "Only new claims may be verified."})
    if documents_verified is not True or eligible is not True:
        raise ValidationError(
            {"verification": "HR must explicitly confirm documents and eligibility."}
        )
    route_for(obj.record, obj.kind)
    obj.status = "pending"
    obj.save(update_fields=["status", "updated_at"])
    record_event(obj, "verified", principal)
    notify(obj.record.user_id, "claim", "Claim verified and sent for approval.")
    return obj


@transaction.atomic
def decide_claim(pk, outcome, principal):
    obj = Claim.objects.select_for_update().select_related("record").get(pk=pk)
    if obj.status != "pending":
        raise ValidationError({"status": "Claim is not pending approval."})
    role, route = current_authority(obj.record, obj.kind, obj.current_step, obj.approval_roles)
    check_authority(principal, role)
    if outcome == "forward":
        if obj.current_step + 1 >= len(route):
            raise ValidationError({"outcome": "No next approval authority exists."})
        obj.current_step += 1
    elif outcome == "approve":
        obj.status = "approved"
    elif outcome == "reject":
        obj.status = "rejected"
    else:
        raise ValidationError({"outcome": "Choose approve, reject, or forward."})
    obj.save(update_fields=["status", "current_step", "updated_at"])
    record_event(obj, outcome, principal, {"step": obj.current_step})
    notify(obj.record.user_id, "claim", f"Claim {outcome}.")
    return obj


@transaction.atomic
def process_claim(pk, payment_status, reference, principal):
    obj = Claim.objects.select_for_update().get(pk=pk)
    if obj.status not in ("approved", "processed"):
        raise ValidationError({"status": "Only approved claims may receive settlement records."})
    if not payment_status or not reference:
        raise ValidationError(
            {"payment_reference": "Payment status and external reference are required."}
        )
    obj.payment_status = payment_status
    obj.payment_reference = reference
    obj.status = "processed"
    obj.save(update_fields=["payment_status", "payment_reference", "status", "updated_at"])
    record_event(
        obj,
        "financial_status_recorded",
        principal,
        {"payment_status": payment_status, "payment_reference": reference},
    )
    notify(obj.record.user_id, "claim", "Claim financial status recorded.")
    return obj
