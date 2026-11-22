"""Reimbursement claim writes and forward-only routing (PHC-BR-04..08, 13, 14)."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.phc.domain.policy import (
    ALREADY_DONE_MESSAGE,
    CLAIM_KIND_MESSAGE,
    CLAIM_WINDOW_MESSAGE,
    PRESCRIPTION_MESSAGE,
    WAITING_MESSAGE,
    expense_within_window,
    is_reimbursable_kind,
)
from modules.phc.domain.state_machine import CLAIM_EXPECTED, next_claim_state
from modules.phc.models import ReimbursementClaim
from modules.phc.selectors import scoping
from modules.phc.services import audit, notifications

CLAIM_NOT_FOUND = "No claim was found for your account. Refresh the claim list and try again."
HISTORY = {
    "review": "PHC review forwarded to Accounts & Audit",
    "verify": "Accounts & Audit verified, forwarded for sanction",
    "sanction_approve": "Sanction approved",
    "sanction_reject": "Sanction rejected (terminal)",
    "payment": "Payment processed, claim reimbursed",
}
AUDIT_ACTION = {
    "review": "claim.review", "verify": "claim.verify",
    "sanction_approve": "claim.sanction_approve",
    "sanction_reject": "claim.sanction_reject", "payment": "claim.payment",
}


@transaction.atomic
def submit(actor, validated: dict) -> ReimbursementClaim:
    """Create a fresh claim; submitted claims are never edited or reopened."""
    if not is_reimbursable_kind(getattr(actor, "kind", "")):
        raise BadRequestError(CLAIM_KIND_MESSAGE)
    if not expense_within_window(validated["expense_date"], timezone.now().date()):
        raise BadRequestError(CLAIM_WINDOW_MESSAGE)
    prescription = scoping.prescription_for_claimant(
        validated["prescription_id"], getattr(actor, "user_id", None))
    if prescription is None:
        raise BadRequestError(PRESCRIPTION_MESSAGE)
    claim = ReimbursementClaim.objects.create(
        employee_id=actor.user_id,
        user_id=actor.user_id,
        prescription=prescription,
        expense_date=validated["expense_date"],
        amount=validated["amount"],
        description=validated.get("description", ""),
        state="submitted",
        stage_actor="PHC Staff",
        action_history=["submitted by employee"],
    )
    audit.record(actor, "claim.submit", "claim", claim.pk, {"state": claim.state})
    notifications.claim_status_notice(claim, "submit")
    return claim


@transaction.atomic
def advance(actor, pk: int, action: str, note: str = "",
            expected_updated_at=None) -> ReimbursementClaim:
    """Move a claim forward under a row lock; a stale client version is a 409."""
    claim = (ReimbursementClaim.objects
             .select_for_update().filter(pk=pk).first())
    if claim is None:
        raise NotFoundError(CLAIM_NOT_FOUND, code="not_found")
    if expected_updated_at is not None and str(claim.updated_at) != str(expected_updated_at):
        raise ConflictError(ALREADY_DONE_MESSAGE, code="conflict")
    expected = CLAIM_EXPECTED[action]
    if claim.state != expected:
        raise NotFoundError(WAITING_MESSAGE, code="not_found")
    target = next_claim_state(claim.state, action)
    claim.state = target
    history = [*list(claim.action_history or []), HISTORY[action]]
    if note and target == "rejected":
        history.append(f"Note: {note}")
    claim.action_history = history
    claim.save()
    audit.record(actor, AUDIT_ACTION[action], "claim", claim.pk,
                 {"state": claim.state})
    notifications.claim_status_notice(claim, action)
    return claim
