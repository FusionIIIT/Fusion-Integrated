from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from modules.iaa.models import IAAApproval, IAAAuditEvent, IAAExpenseRequest, IATravelClaim


def actor_id(actor):
    value = getattr(actor, "user_id", None)
    if value is None:
        raise PermissionDenied("An institute user identity is required.")
    return int(value)


def audit(*, kind, pk, action, actor, role="", before=None, after=None, remarks=""):
    IAAAuditEvent.objects.create(aggregate_type=kind, aggregate_id=pk, action=action,
        actor_user_id=actor_id(actor), actor_role=role or "", before=before or {},
        after=after or {}, remarks=remarks)


@transaction.atomic
def submit_expense(request_obj, actor):
    uid = actor_id(actor)
    if request_obj.claimant_user_id != uid:
        raise PermissionDenied("Only the claimant may submit this request.")
    if request_obj.status != "draft":
        raise ValidationError("Only draft requests can be submitted.")
    if not request_obj.title.strip() or request_obj.amount <= 0 or not request_obj.financial_year:
        raise ValidationError("Title, positive amount and financial year are required.")
    old = request_obj.status
    request_obj.status = "submitted"
    request_obj.submitted_at = timezone.now()
    request_obj.locked_at = timezone.now()
    request_obj.save(update_fields=["status", "submitted_at", "locked_at", "updated_at"])
    audit(kind="expense", pk=request_obj.pk, action="submitted", actor=actor,
          before={"status": old}, after={"status": request_obj.status})
    return request_obj


@transaction.atomic
def decide_expense(request_obj, actor, *, decision, remarks, level=1, role=""):
    uid = actor_id(actor)
    if request_obj.claimant_user_id == uid:
        raise PermissionDenied("Segregation of duties: claimant cannot approve own request.")
    if request_obj.status not in ("pending_approval", "submitted", "finance_review"):
        raise ValidationError("This request is not awaiting an approval decision.")
    if decision not in ("approved", "rejected", "escalated"):
        raise ValidationError("Unsupported decision.")
    if not remarks or not remarks.strip():
        raise ValidationError({"remarks": "Decision remarks are required."})
    IAAApproval.objects.create(request=request_obj, level=level,
        approver_user_id=uid, approver_role=role, decision=decision, remarks=remarks)
    before = request_obj.status
    if decision == "approved":
        request_obj.status = "approved"
    elif decision == "rejected":
        request_obj.status = "rejected"
    else:
        request_obj.status = "pending_approval"
    request_obj.save(update_fields=["status", "updated_at"])
    audit(kind="expense", pk=request_obj.pk, action=f"approval_{decision}", actor=actor,
          role=role, before={"status": before}, after={"status": request_obj.status}, remarks=remarks)
    return request_obj


@transaction.atomic
def submit_travel(claim, actor):
    uid = actor_id(actor)
    if claim.claimant_user_id != uid:
        raise PermissionDenied("Only the claimant may submit this TA claim.")
    if claim.status != "draft" or claim.end_date < claim.start_date or claim.amount <= 0:
        raise ValidationError("TA claim dates, amount or status are invalid.")
    claim.status = "submitted"
    claim.submitted_at = timezone.now()
    claim.save(update_fields=["status", "submitted_at", "updated_at"])
    audit(kind="travel_claim", pk=claim.pk, action="submitted", actor=actor,
          after={"status": claim.status})
    return claim
