from django.db import transaction
from rest_framework.exceptions import NotFound

from core.api.exceptions import BadRequestError  # Updated import
from modules.phc.domain.reimbursement import (
    PENDING_PHC_REVIEW,
    PENDING_ACCOUNTS_VERIFICATION,
    PENDING_SANCTION,
    APPROVED_FOR_PAYMENT,
    REIMBURSED,
    REJECTED,
    validate_claim_submission,  # Import the validate_claim_submission function
    get_next_status,  # Import the get_next_status function
)
from modules.phc.models import ReimbursementClaim, Prescription, ReimbursementPayment  # Import the ReimbursementPayment model
from modules.phc.services.common import record_audit, notify

@transaction.atomic
def create_claim(claimant_user_id: int, claimant_kind: str, prescription_id: int, expense_date, claimed_amount, description: str) -> ReimbursementClaim:
    """Create a reimbursement claim."""
    from django.conf import settings
    window_days = getattr(settings, "PHC_REIMBURSEMENT_WINDOW_DAYS", 30)
    prescription = Prescription.objects.filter(id=prescription_id).first()
    if not prescription:
        raise NotFound("Prescription not found")  # PHC-BR-11

    validate_claim_submission(claimant_user_kind=claimant_kind, prescription_patient_user_id=prescription.patient_user_id, expense_date=expense_date, window_days=window_days)

    claim = ReimbursementClaim.objects.create(
        claimant_user_id=claimant_user_id,
        prescription=prescription,
        expense_date=expense_date,
        claimed_amount=claimed_amount,
        description=description,
        status=PENDING_PHC_REVIEW,
    )

    record_audit(entity_type="ReimbursementClaim", entity_id=claim.id, action="submit", actor_user_id=claimant_user_id, from_status="", to_status=PENDING_PHC_REVIEW)  # PHC-BR-09

    notify(recipient_user_id=claimant_user_id, kind="claim_submitted", message=f"Your claim for prescription {prescription.id} has been submitted.")

    return claim


@transaction.atomic
def transition_claim(claim_id: int, action: str, actor_user_id: int, actor_role: str, note: str = "") -> ReimbursementClaim:
    """Transition a reimbursement claim through review."""
    from core.api.exceptions import BadRequestError  # Updated import

    claim = ReimbursementClaim.objects.select_for_update().filter(id=claim_id).first()
    if not claim:
        raise NotFound("Claim not found")  # PHC-BR-11

    next_status = get_next_status(claim.status, action)
    if next_status is None:
        raise BadRequestError(code="not_pending", detail=f"Invalid action '{action}' for status {claim.status}")  # PHC-BR-08

    claim.status = next_status
    claim.save()

    record_audit(entity_type="ReimbursementClaim", entity_id=claim.id, action=action, actor_user_id=actor_user_id, from_status=claim.status, to_status=next_status, note=note)  # PHC-BR-09

    notify(recipient_user_id=claim.claimant_user_id, kind="claim_status_changed", message=f"Your claim status has been changed to {next_status}.")

    return claim


@transaction.atomic
def pay_claim(claim_id: int, actor_user_id: int, actor_role: str, paid_on, reference: str) -> ReimbursementPayment:
    """Record payment for a reimbursement claim."""
    from core.api.exceptions import BadRequestError  # Updated import

    claim = ReimbursementClaim.objects.select_for_update().filter(id=claim_id).first()
    if not claim:
        raise NotFound("Claim not found")  # PHC-BR-11

    if claim.status != APPROVED_FOR_PAYMENT:
        raise BadRequestError(code="not_pending", detail=f"Invalid action 'record_payment' for status {claim.status}")  # PHC-BR-08

    claim.status = REIMBURSED
    claim.save()

    payment = ReimbursementPayment.objects.create(
        claim=claim,
        paid_on=paid_on,
        reference=reference,
        recorded_by_user_id=actor_user_id,
    )

    record_audit(entity_type="ReimbursementClaim", entity_id=claim.id, action="record_payment", actor_user_id=actor_user_id, from_status=APPROVED_FOR_PAYMENT, to_status=REIMBURSED)  # PHC-BR-09

    notify(recipient_user_id=claim.claimant_user_id, kind="payment_recorded", message=f"Your claim has been paid on {paid_on} with reference {reference}.")

    return payment
