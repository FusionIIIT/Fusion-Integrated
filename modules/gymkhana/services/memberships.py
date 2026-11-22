"""Membership enrolment (BW-GYM-01: UC-GYM-004, UC-GYM-005)."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, DomainError, NotFoundError
from modules.gymkhana.domain import state_machine as sm
from modules.gymkhana.models import Membership
from modules.gymkhana.selectors import scoping
from modules.gymkhana.services import audit
from modules.gymkhana.services.authz import require

P_APPLY = "gymkhana.membership.create"
P_APPROVE = "gymkhana.membership.approve"
MAX_BATCH = 100
MAX_REMARKS = 1000

_DUPLICATE = ("You have already applied to this club. Your existing application "
              "is unchanged.")


def apply(*, actor, club_id: int, description: str) -> Membership:
    """UC-GYM-004: an open application to a confirmed club, once per club."""
    require(actor, P_APPLY)
    sm.resolve(sm.MEMBERSHIP, sm.NONE, sm.APPLY, sm.STUDENT)
    # BR-GYM-007: an open club is not visible to a student, so it is not found.
    club = scoping.clubs_for(actor).filter(pk=club_id, status=sm.CONFIRMED).first()
    if club is None:
        raise NotFoundError("No such club is open for membership.")
    text = (description or "").strip()
    if not text:
        raise DomainError("Describe why you want to join or list your achievements.",
                          code="missing_field",
                          details=[{"field": "description",
                                    "message": "Enter a description or achievements."}])
    # BR-GYM-009, checked first for the message and held by the unique constraint.
    if Membership.objects.filter(club=club, user_id=actor.user_id).exists():
        raise ConflictError(_DUPLICATE, code="duplicate_application")
    try:
        with transaction.atomic():
            membership = Membership.objects.create(
                club=club, user_id=actor.user_id, description=text, status=sm.OPEN)
            audit.record("membership.applied", object_type="membership",
                         object_id=membership.pk, actor=actor, club_id=club.pk,
                         status=sm.OPEN)
    except IntegrityError as exc:
        raise ConflictError(_DUPLICATE, code="duplicate_application") from exc
    return membership


@dataclass(frozen=True)
class ApprovalOutcome:
    id: int
    outcome: str
    code: str
    message: str


def approve_many(*, actor, ids: Sequence[int], remarks: str = "") -> list[ApprovalOutcome]:
    """UC-GYM-005: each application is decided on its own; one refusal never undoes another."""
    require(actor, P_APPROVE)
    unique = list(dict.fromkeys(int(i) for i in ids))
    if not unique:
        raise BadRequestError("Choose at least one application to approve.",
                              code="nothing_selected")
    if len(unique) > MAX_BATCH:
        raise BadRequestError(f"Approve at most {MAX_BATCH} applications at a time.",
                              code="too_many")
    remarks = (remarks or "").strip()
    if len(remarks) > MAX_REMARKS:
        raise DomainError(f"Remarks can be at most {MAX_REMARKS} characters.",
                          code="remarks_too_long")
    return [_approve_one(actor, membership_id, remarks) for membership_id in unique]


@transaction.atomic
def _approve_one(actor, membership_id: int, remarks: str) -> ApprovalOutcome:
    membership = (Membership.objects.select_for_update()
                  .filter(pk=membership_id,
                          club__in=scoping.led_clubs(actor).values("pk")).first())
    if membership is None:
        return ApprovalOutcome(membership_id, "refused", "not_found",
                               "No such application for a club you lead.")
    # H2: an applicant who also leads the club cannot approve themselves.
    if membership.user_id == actor.user_id:
        return ApprovalOutcome(membership_id, "refused", "self_approval",
                               "You cannot approve your own application. The other "
                               "club leader can approve it.")
    try:
        t = sm.resolve(sm.MEMBERSHIP, membership.status, sm.APPROVE, sm.CLUB_HEAD)
    except sm.InvalidTransition:
        return ApprovalOutcome(membership_id, "refused", "already_confirmed",
                               "This application is already approved.")
    membership.status = t.to
    membership.remarks = remarks
    membership.approved_by_user_id = actor.user_id
    membership.approved_at = timezone.now()
    membership.save(update_fields=["status", "remarks", "approved_by_user_id",
                                   "approved_at", "updated_at"])
    audit.record("membership.approved", object_type="membership",
                 object_id=membership.pk, actor=actor, club_id=membership.club_id,
                 status=t.to)
    return ApprovalOutcome(membership_id, "approved", "approved", "Approved.")
