"""Claim submission (PHC-UC-04) and the one choke point every later claim move goes through."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import (
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.phc.domain import rules
from modules.phc.domain.state_machine import (
    CLAIM_TRANSITIONS,
    ClaimStatus,
    IllegalTransition,
    resolve,
)
from modules.phc.models import ClaimAction, ReimbursementClaim, ReimbursementPolicy
from modules.phc.selectors import scoping
from modules.phc.services import trail

STATUS_LABELS = dict(ClaimStatus.CHOICES)


class PolicyMissingError(ConflictError):
    code = "policy_missing"
    message = ("Reimbursement claims cannot be accepted yet because no submission window has "
               "been configured. Ask the PHC office to configure it.")


def active_policy(on: date) -> ReimbursementPolicy | None:
    return (ReimbursementPolicy.objects.filter(effective_from__lte=on)
            .order_by("-effective_from").first())


@transaction.atomic
def configure_policy(*, window_days: int, includes_last_day: bool, effective_from: date,
                     actor_user_id: int | None = None) -> ReimbursementPolicy:
    # Policy is never edited: a new version supersedes the old from its effective date.
    if window_days <= 0:
        raise DomainError("The submission window must be at least one day.",
                          code="invalid_window")
    if ReimbursementPolicy.objects.filter(effective_from=effective_from).exists():
        raise ConflictError("A policy already takes effect on that date; choose a later one.",
                            code="policy_exists")
    return ReimbursementPolicy.objects.create(window_days=window_days,
                                              includes_last_day=includes_last_day,
                                              effective_from=effective_from,
                                              created_by_user_id=actor_user_id)


@transaction.atomic
def submit_claim(*, actor, prescription_id: int, expense_date: date, amount: Decimal,
                 description: str) -> ReimbursementClaim:
    try:
        # PHC-BR-04 first: a student learns they are ineligible, not that a field is wrong.
        rules.require_employee(actor.kind)
    except rules.RuleViolation as exc:
        raise PermissionDeniedError(exc.message, code=exc.code) from exc
    # PHC-BR-05
    prescription = scoping.own_prescriptions(actor).filter(pk=prescription_id).first()
    if prescription is None:
        raise DomainError("Choose a prescription recorded for you at the PHC.",
                          code="invalid_prescription")
    today = timezone.localdate()
    policy = active_policy(today)
    if policy is None:
        raise PolicyMissingError()
    try:
        # PHC-BR-06
        rules.check_submission_window(expense_date, today, rules.SubmissionWindow(
            policy.window_days, policy.includes_last_day))
    except rules.RuleViolation as exc:
        raise DomainError(exc.message, code=exc.code) from exc
    claim = ReimbursementClaim.objects.create(
        user_id=actor.user_id, prescription=prescription, expense_date=expense_date,
        amount=amount, description=description, submitted_at=timezone.now())
    ClaimAction.objects.create(claim=claim, actor_user_id=actor.user_id, event="submit",
                               to_status=claim.status)
    trail.audit(actor_user_id=actor.user_id, resource_type="reimbursement_claim",
                resource_id=claim.pk, action="submit", details={"to": claim.status})
    return claim


@transaction.atomic
def transition_claim(*, actor, claim_id: int, event: str, note: str = "") -> ReimbursementClaim:
    # CW-PHC-01: lock, refuse terminal or wrong-office moves, record, audit, notify.
    claim = (ReimbursementClaim.objects.select_for_update()
             .filter(pk=claim_id).first())
    if claim is None or not scoping.claims_for(actor).filter(pk=claim_id).exists():
        raise NotFoundError("That reimbursement claim does not exist.")
    if claim.user_id == actor.user_id:
        raise PermissionDeniedError("You cannot act on your own reimbursement claim.",
                                    code="own_claim")
    if claim.status in ClaimStatus.TERMINAL:
        raise ConflictError(
            f"This claim is already {STATUS_LABELS[claim.status].lower()} and cannot change. "
            "A new claim must be submitted instead.", code="claim_closed")
    try:
        move = resolve(CLAIM_TRANSITIONS, claim.status, event, actor.permissions)
    except IllegalTransition as exc:
        raise ConflictError(
            f"This claim is {STATUS_LABELS[claim.status].lower()}, so it cannot be "
            f"{event}ed by your office now.", code="illegal_transition") from exc
    previous = claim.status
    claim.status = move.target
    claim.save(update_fields=("status", "updated_at"))
    ClaimAction.objects.create(claim=claim, actor_user_id=actor.user_id, event=event,
                               from_status=previous, to_status=move.target, note=note)
    # PHC-BR-09
    trail.audit(actor_user_id=actor.user_id, resource_type="reimbursement_claim",
                resource_id=claim.pk, action=event,
                details={"from": previous, "to": move.target})
    # PHC-BR-13
    trail.notify(recipient_user_id=claim.user_id, kind="claim_status",
                 message=f"Your reimbursement claim #{claim.pk} is now "
                         f"{STATUS_LABELS[move.target].lower()}.",
                 resource_type="reimbursement_claim", resource_id=claim.pk)
    return claim
