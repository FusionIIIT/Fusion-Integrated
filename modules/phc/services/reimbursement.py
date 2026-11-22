"""PHC services: medical bill reimbursement.

Implements CW-PHC-01 / BW-PHC-01 / BW-PHC-02 state machine.
PHC-UC-04, PHC-UC-15, PHC-UC-19, PHC-UC-20, PHC-UC-21.
PHC-BR-04, PHC-BR-05, PHC-BR-06, PHC-BR-08, PHC-BR-09, PHC-BR-13, PHC-BR-14.
AFR-PHC-013 … AFR-PHC-021, AFR-PHC-038.
"""

from __future__ import annotations

import logging
from datetime import date as date_type
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.phc.domain.reimbursement import (
    ReimbursementValidationError,
    check_employee_eligibility,
    check_submission_window,
)
from modules.phc.domain.state_machine import (
    InvalidClaimTransition,
    ReimbursementState,
    advance_claim,
)
from modules.phc.models import (
    Prescription,
    ReimbursementAudit,
    ReimbursementClaim,
    ReimbursementConfig,
)
from modules.phc.services import notifications

log = logging.getLogger("fusion.phc.reimbursement")


def _config() -> ReimbursementConfig:
    obj, _ = ReimbursementConfig.objects.get_or_create(pk=1)
    return obj


def submit_claim(
    *,
    claimant_user_id: int,
    claimant_kind: str,  # "faculty" / "staff" (PHC-BR-04)
    prescription_id: int,
    amount_claimed: Decimal,
    description: str = "",
    submission_date: date_type | None = None,
) -> ReimbursementClaim:
    """PHC-UC-04: Employee submits a reimbursement claim.

    Guards: PHC-BR-04 (employee only), PHC-BR-05 (prescription linkage),
    PHC-BR-06 (submission window), PHC-BR-08 (enters pending_phc_review).
    """
    # PHC-BR-04
    try:
        check_employee_eligibility(claimant_kind)
    except ReimbursementValidationError as exc:
        raise PermissionDeniedError(str(exc)) from exc

    # PHC-BR-05: prescription must exist and belong to the claimant
    try:
        rx = Prescription.objects.get(pk=prescription_id, user_id=claimant_user_id)
    except Prescription.DoesNotExist:
        raise ConflictError(
            "No matching prescription found for this claimant. "
            "A claim must be linked to a valid prescription recorded in the system.",
            code="prescription_not_found",
        ) from None

    if rx.expense_date is None:
        raise ConflictError(
            "The linked prescription must include the medical expense date.",
            code="expense_date_required",
        )

    # PHC-BR-06: submission window
    today = submission_date or timezone.localdate()
    cfg = _config()
    try:
        check_submission_window(rx.expense_date, today, cfg.submission_window_days)
    except ReimbursementValidationError as exc:
        raise ConflictError(str(exc), code="submission_window_expired") from exc

    with transaction.atomic():
        claim = ReimbursementClaim.objects.create(
            user_id=claimant_user_id,
            prescription=rx,
            amount_claimed=amount_claimed,
            description=description,
            status=ReimbursementState.PENDING_PHC_REVIEW,
        )
        ReimbursementAudit.objects.create(
            claim=claim,
            from_status="",
            to_status=ReimbursementState.PENDING_PHC_REVIEW,
            actor_user_id=claimant_user_id,
            actor_role="employee",
            notes="Claim submitted.",
        )
    # PHC-BR-13: notify claimant (echoes their own submission for record)
    notifications.notify_claim_status_changed(
        claim=claim,
        to_status=ReimbursementState.PENDING_PHC_REVIEW,
        actor_user_id=claimant_user_id,
    )
    log.info("phc.claim.submitted claim=%s claimant=%s", claim.pk, claimant_user_id)
    return claim


def _advance(
    *,
    claim: ReimbursementClaim,
    to_status: str,
    actor_user_id: int,
    actor_role: str,
    notes: str = "",
) -> ReimbursementClaim:
    """Internal: validate + advance a claim one state, write audit + notification."""
    try:
        advance_claim(claim.status, to_status, actor_role)
    except InvalidClaimTransition as exc:
        raise ConflictError(str(exc), code="invalid_claim_transition") from exc

    with transaction.atomic():
        old_status = claim.status
        claim.status = to_status
        claim.save(update_fields=["status", "updated_at"])
        ReimbursementAudit.objects.create(
            claim=claim,
            from_status=old_status,
            to_status=to_status,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            notes=notes,
        )
    # PHC-BR-13
    notifications.notify_claim_status_changed(
        claim=claim,
        to_status=to_status,
        actor_user_id=actor_user_id,
    )
    log.info(
        "phc.claim.advanced claim=%s %s→%s by=%s", claim.pk, old_status, to_status, actor_user_id
    )
    return claim


def phc_review_forward(*, claim: ReimbursementClaim, actor_user_id: int) -> ReimbursementClaim:
    """PHC-UC-15: PHC Staff forwards claim to Accounts & Audit."""
    return _advance(
        claim=claim,
        to_status=ReimbursementState.PENDING_ACCOUNTS,
        actor_user_id=actor_user_id,
        actor_role="phc_staff",
        notes="Forwarded to Accounts & Audit by PHC Staff.",
    )


def accounts_verify(*, claim: ReimbursementClaim, actor_user_id: int) -> ReimbursementClaim:
    """PHC-UC-19: Accounts & Audit completes financial verification."""
    return _advance(
        claim=claim,
        to_status=ReimbursementState.PENDING_SANCTION,
        actor_user_id=actor_user_id,
        actor_role="accounts_audit",
        notes="Financial verification completed by Accounts & Audit.",
    )


def authority_decide(
    *,
    claim: ReimbursementClaim,
    actor_user_id: int,
    approve: bool,
    notes: str = "",
) -> ReimbursementClaim:
    """PHC-UC-20: Approving Authority approves or rejects the sanction.

    Rejection is terminal (PHC-BR-14, BW-PHC-02).
    """
    to_status = ReimbursementState.APPROVED_FOR_PAYMENT if approve else ReimbursementState.REJECTED
    return _advance(
        claim=claim,
        to_status=to_status,
        actor_user_id=actor_user_id,
        actor_role="approving_authority",
        notes=notes or ("Approved for payment." if approve else "Rejected."),
    )


def process_payment(*, claim: ReimbursementClaim, actor_user_id: int) -> ReimbursementClaim:
    """PHC-UC-21: Accounts & Audit records completed payment."""
    return _advance(
        claim=claim,
        to_status=ReimbursementState.REIMBURSED,
        actor_user_id=actor_user_id,
        actor_role="accounts_audit",
        notes="Payment processed by Accounts & Audit.",
    )
