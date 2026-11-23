from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.directory.contracts import is_employee
from modules.phc.domain.reimbursements import (
    claim_transition,
    validate_claim_amount,
    validate_submission_date,
)
from modules.phc.models import (
    Prescription,
    ReimbursementAction,
    ReimbursementClaim,
    ReimbursementPolicy,
)
from modules.phc.services.common import audit
from modules.phc.services.notifications import enqueue


def _policy_for(day):
    policy = ReimbursementPolicy.objects.filter(effective_period__contains=day).first()
    if policy is None:
        raise ConflictError(
            "The PHC reimbursement policy is not configured; contact the PHC office.",
                            code="policy_missing")
    return policy


def submit_claim(*, claimant_user_id: int, prescription_id: int, claim_amount,
                 expense_date, bill_reference: str, remarks: str):
    today = timezone.localdate()
    if claimant_user_id not in is_employee([claimant_user_id]):
        raise ConflictError("Only current institute employees may submit reimbursement claims.",
                            code="employee_required")
    try:
        validate_claim_amount(claim_amount)
        policy = _policy_for(today)
        validate_submission_date(expense_date, today, policy.submission_window_days)
    except ValueError as exc:
        raise BadRequestError(str(exc), code="claim_invalid") from exc
    with transaction.atomic():
        prescription = Prescription.objects.select_related("visit").filter(
            pk=prescription_id).first()
        if prescription is None or prescription.visit.patient_user_id != claimant_user_id:
            raise NotFoundError("Choose a prescription recorded for your own patient record.",
                                code="prescription_not_found")
        claim = ReimbursementClaim.objects.create(
            claimant_user_id=claimant_user_id,
            prescription=prescription,
            claim_amount=claim_amount,
            expense_date=expense_date,
            bill_reference=bill_reference,
            remarks=remarks,
            submitted_at=timezone.now(),
        )
        ReimbursementAction.objects.create(
            claim=claim, from_state="absent", to_state=claim.state,
            event="submit", actor_user_id=claimant_user_id)
        audit(actor_user_id=claimant_user_id, action="reimbursement.submitted",
              object_type="reimbursement_claim", object_id=claim.pk,
              metadata={"state": claim.state})
        enqueue(
            event_key=f"claim:{claim.pk}:{claim.state}",
            recipient_user_id=claimant_user_id,
            event_type="reimbursement_status",
            payload={"target_type": "reimbursement_claim", "target_id": claim.pk,
                     "state": claim.state},
        )
        return claim


def transition_claim(*, claim_id: int, actor_user_id: int, actor_role: str,
                     event: str, scope):
    with transaction.atomic():
        claim = scope.select_for_update().filter(pk=claim_id).first()
        if claim is None:
            raise NotFoundError("That reimbursement claim is not available.",
                                code="claim_not_found")
        try:
            new_state = claim_transition(claim.state, event, actor_role)
        except PermissionError as exc:
            raise ConflictError(str(exc), code="actor_not_allowed") from exc
        except LookupError as exc:
            raise ConflictError(str(exc), code="invalid_transition") from exc
        previous = claim.state
        claim.state = new_state
        claim.save(update_fields=["state", "updated_at"])
        ReimbursementAction.objects.create(
            claim=claim, from_state=previous, to_state=new_state,
            event=event, actor_user_id=actor_user_id)
        audit(actor_user_id=actor_user_id, action=f"reimbursement.{event}",
              object_type="reimbursement_claim", object_id=claim.pk,
              metadata={"from": previous, "to": new_state})
        enqueue(
            event_key=f"claim:{claim.pk}:{new_state}",
            recipient_user_id=claim.claimant_user_id,
            event_type="reimbursement_status",
            payload={"target_type": "reimbursement_claim", "target_id": claim.pk,
                     "state": new_state},
        )
        return claim
