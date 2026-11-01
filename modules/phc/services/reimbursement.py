"""Medical Bill Reimbursement services (CFR-PHC-003, CFR-PHC-004, CFR-PHC-005)."""
from datetime import date
from decimal import Decimal
from django.utils import timezone

from modules.phc.domain.entities import ReimbursementStatus
from modules.phc.domain.errors import (
    ClaimImmutableError,
    IneligibleClaimantError,
    PrescriptionRequiredError,
    SubmissionWindowExpiredError,
)
from modules.phc.domain.state_machine import ReimbursementStateMachine
from modules.phc.models.patient_records import Prescription
from modules.phc.models.reimbursement import ReimbursementActionHistory, ReimbursementClaim
from modules.phc.services.audit import record_audit_event
from modules.phc.services.notifications import notify_user

SUBMISSION_WINDOW_DAYS = 90


def submit_reimbursement_claim(
    claimant_user_id: int,
    claimant_kind: str,
    claimant_username: str,
    prescription_id: int,
    expense_date: date,
    amount_claimed: Decimal,
    bills_document_url: str = "",
    remarks: str = "",
) -> ReimbursementClaim:
    """Submits a medical bill reimbursement claim (CFR-PHC-003, UC-PHC-04).

    Enforces:
    - PHC-BR-04: Employee only (students strictly denied)
    - PHC-BR-05: Valid prescription recorded for claimant
    - PHC-BR-06: Submission window
    - PHC-BR-08: Initial state 'Pending PHC Review'
    - PHC-BR-09: Audit record
    - PHC-BR-13: Status notification
    """
    # 1. Eligibility Check: Employee Only (BR-04 / AFR-013)
    if claimant_kind.lower() == "student":
        raise IneligibleClaimantError(
            "PHC-BR-04: Medical bill reimbursement submission is restricted to institute employees. "
            "Students are not eligible to submit reimbursement claims."
        )

    # 2. Prescription Prerequisite Check (BR-05 / AFR-014)
    try:
        prescription = Prescription.objects.get(id=prescription_id)
    except Prescription.DoesNotExist:
        raise PrescriptionRequiredError("PHC-BR-05: Referenced prescription does not exist in the system.")

    if prescription.patient_user_id != claimant_user_id:
        raise PrescriptionRequiredError(
            "PHC-BR-05: The prescription must belong to the employee submitting the reimbursement claim."
        )

    # 3. Submission Window Check (BR-06 / AFR-015)
    today = timezone.now().date()
    days_elapsed = (today - expense_date).days
    if days_elapsed < 0:
        raise SubmissionWindowExpiredError("Medical expense date cannot be in the future.")
    if days_elapsed > SUBMISSION_WINDOW_DAYS:
        raise SubmissionWindowExpiredError(
            f"PHC-BR-06: The reimbursement claim was submitted after the allowed {SUBMISSION_WINDOW_DAYS}-day window. "
            f"Days elapsed: {days_elapsed}."
        )

    # Generate claim number
    claim_count = ReimbursementClaim.objects.count() + 1
    claim_number = f"MED-CLM-{today.year}-{claim_count:04d}"

    claim = ReimbursementClaim.objects.create(
        claim_number=claim_number,
        claimant_user_id=claimant_user_id,
        prescription=prescription,
        expense_date=expense_date,
        amount_claimed=amount_claimed,
        bills_document_url=bills_document_url.strip(),
        status=ReimbursementStatus.PENDING_PHC_REVIEW.value,
        remarks=remarks.strip(),
    )

    # Record action history
    ReimbursementActionHistory.objects.create(
        claim=claim,
        action="SUBMIT_CLAIM",
        from_status="Draft",
        to_status=claim.status,
        actor_user_id=claimant_user_id,
        actor_role="Employee",
        comments="Claim submitted by employee.",
    )

    # Audit record (BR-09)
    record_audit_event(
        target_type="REIMBURSEMENT_CLAIM",
        target_id=claim.claim_number,
        action="SUBMIT",
        details={"amount": str(amount_claimed), "claimant": claimant_user_id},
        actor_user_id=claimant_user_id,
        actor_username=claimant_username,
    )

    # Notification to claimant (BR-13)
    notify_user(
        recipient_user_id=claimant_user_id,
        notification_type="REIMBURSEMENT_STATUS",
        title=f"Claim {claim.claim_number} Submitted",
        message=f"Your claim for ₹{amount_claimed} is currently Pending PHC Review.",
    )

    return claim


def review_claim_phc(
    claim_id: int,
    actor_user_id: int,
    actor_username: str,
    comments: str = "",
) -> ReimbursementClaim:
    """PHC Staff review -> forwards to Accounts & Audit (AFR-PHC-018, UC-PHC-15, CW-PHC-01 Step 2)."""
    claim = ReimbursementClaim.objects.get(id=claim_id)
    new_status = ReimbursementStateMachine.transition_phc_review_forward(claim.status)

    old_status = claim.status
    claim.status = new_status.value
    claim.save()

    ReimbursementActionHistory.objects.create(
        claim=claim,
        action="PHC_REVIEW_FORWARD",
        from_status=old_status,
        to_status=claim.status,
        actor_user_id=actor_user_id,
        actor_role="PHC Staff",
        comments=comments.strip(),
    )

    record_audit_event(
        target_type="REIMBURSEMENT_CLAIM",
        target_id=claim.claim_number,
        action="PHC_FORWARD",
        details={"old_status": old_status, "new_status": claim.status, "comments": comments},
        actor_user_id=actor_user_id,
        actor_username=actor_username,
    )

    notify_user(
        recipient_user_id=claim.claimant_user_id,
        notification_type="REIMBURSEMENT_STATUS",
        title=f"Claim {claim.claim_number} Verified by PHC",
        message=f"Your claim has completed PHC review and forwarded to Accounts & Audit for financial verification.",
    )

    return claim


def verify_claim_accounts(
    claim_id: int,
    actor_user_id: int,
    actor_username: str,
    amount_verified: Decimal | None = None,
    comments: str = "",
) -> ReimbursementClaim:
    """Accounts & Audit financial verification -> forwards to Approving Authority (AFR-PHC-019, UC-PHC-19)."""
    claim = ReimbursementClaim.objects.get(id=claim_id)
    new_status = ReimbursementStateMachine.transition_accounts_verify(claim.status)

    old_status = claim.status
    claim.status = new_status.value
    if amount_verified is not None:
        claim.amount_approved = amount_verified
    claim.save()

    ReimbursementActionHistory.objects.create(
        claim=claim,
        action="ACCOUNTS_VERIFY",
        from_status=old_status,
        to_status=claim.status,
        actor_user_id=actor_user_id,
        actor_role="Accounts & Audit",
        comments=comments.strip(),
    )

    record_audit_event(
        target_type="REIMBURSEMENT_CLAIM",
        target_id=claim.claim_number,
        action="ACCOUNTS_VERIFY",
        details={"old_status": old_status, "new_status": claim.status, "amount_verified": str(amount_verified)},
        actor_user_id=actor_user_id,
        actor_username=actor_username,
    )

    notify_user(
        recipient_user_id=claim.claimant_user_id,
        notification_type="REIMBURSEMENT_STATUS",
        title=f"Claim {claim.claim_number} Financially Verified",
        message=f"Your claim has been verified by Accounts & Audit and forwarded to the Approving Authority for sanction.",
    )

    return claim


def decide_claim_sanction(
    claim_id: int,
    approve: bool,
    actor_user_id: int,
    actor_username: str,
    sanctioned_amount: Decimal | None = None,
    comments: str = "",
) -> ReimbursementClaim:
    """Approving Authority sanction decision (AFR-PHC-020, UC-PHC-20, BW-PHC-01, BW-PHC-02)."""
    claim = ReimbursementClaim.objects.get(id=claim_id)
    new_status = ReimbursementStateMachine.transition_sanction_decision(claim.status, approve=approve)

    old_status = claim.status
    claim.status = new_status.value
    if approve and sanctioned_amount is not None:
        claim.amount_approved = sanctioned_amount
    elif approve and claim.amount_approved is None:
        claim.amount_approved = claim.amount_claimed
    claim.save()

    action_name = "SANCTION_APPROVE" if approve else "SANCTION_REJECT"
    ReimbursementActionHistory.objects.create(
        claim=claim,
        action=action_name,
        from_status=old_status,
        to_status=claim.status,
        actor_user_id=actor_user_id,
        actor_role="Approving Authority",
        comments=comments.strip(),
    )

    record_audit_event(
        target_type="REIMBURSEMENT_CLAIM",
        target_id=claim.claim_number,
        action=action_name,
        details={"old_status": old_status, "new_status": claim.status, "comments": comments},
        actor_user_id=actor_user_id,
        actor_username=actor_username,
    )

    # PHC-BR-13: Explicitly notify claimant of sanction outcome (including rejection)
    if approve:
        msg = f"Your claim {claim.claim_number} for ₹{claim.amount_approved} has been sanctioned and approved for payment."
    else:
        msg = f"Your claim {claim.claim_number} has been Rejected by the Approving Authority. Reason: {comments or 'Sanction denied'}."

    notify_user(
        recipient_user_id=claim.claimant_user_id,
        notification_type="REIMBURSEMENT_STATUS",
        title=f"Claim {claim.claim_number} Sanction: {claim.status}",
        message=msg,
    )

    return claim


def process_claim_payment(
    claim_id: int,
    actor_user_id: int,
    actor_username: str,
    payment_reference: str = "",
    comments: str = "",
) -> ReimbursementClaim:
    """Accounts & Audit payment completion -> marks Reimbursed (AFR-PHC-021, UC-PHC-21)."""
    claim = ReimbursementClaim.objects.get(id=claim_id)
    new_status = ReimbursementStateMachine.transition_payment_process(claim.status)

    old_status = claim.status
    claim.status = new_status.value
    claim.save()

    combined_comments = f"Payment Ref: {payment_reference}. {comments}".strip()
    ReimbursementActionHistory.objects.create(
        claim=claim,
        action="PAYMENT_PROCESSED",
        from_status=old_status,
        to_status=claim.status,
        actor_user_id=actor_user_id,
        actor_role="Accounts & Audit",
        comments=combined_comments,
    )

    record_audit_event(
        target_type="REIMBURSEMENT_CLAIM",
        target_id=claim.claim_number,
        action="PAYMENT_PROCESSED",
        details={"old_status": old_status, "new_status": claim.status, "payment_ref": payment_reference},
        actor_user_id=actor_user_id,
        actor_username=actor_username,
    )

    # PHC-BR-13: Notify claimant of payment completion
    notify_user(
        recipient_user_id=claim.claimant_user_id,
        notification_type="REIMBURSEMENT_STATUS",
        title=f"Claim {claim.claim_number} Reimbursed",
        message=f"Payment of ₹{claim.amount_approved or claim.amount_claimed} has been processed. Claim is now closed as Reimbursed.",
    )

    return claim
