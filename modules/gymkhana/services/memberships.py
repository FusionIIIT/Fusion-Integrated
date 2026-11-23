"""Membership services for Gymkhana."""

from __future__ import annotations

import datetime

from django.db import IntegrityError, transaction

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.gymkhana.domain.constants import (
    MEMBERSHIP_STATUS_OPEN,
)
from modules.gymkhana.domain.exceptions import DomainError
from modules.gymkhana.domain.state_machines import transition_membership
from modules.gymkhana.domain.validation import (
    validate_club_is_confirmed,
    validate_not_own_application,
)
from modules.gymkhana.models.club import Club
from modules.gymkhana.models.membership import ClubMembership
from modules.gymkhana.selectors.scoping import reviewable_memberships


@transaction.atomic
def apply_membership(*, club_id: int, student_id: int, description: str = "") -> ClubMembership:
    """Apply to a confirmed club (UC-GYM-004, CFR-GYM-004, AFR-GYM-016, AFR-GYM-019, BW-GYM-01)."""
    club = Club.objects.filter(id=club_id).first()
    if not club:
        raise NotFoundError(f"Club {club_id} not found.")

    try:
        validate_club_is_confirmed(club.status)
    except DomainError as exc:
        raise ConflictError(str(exc)) from exc

    # Other clubs stay open to the student (BR-GYM-008, AFR-GYM-017, AFR-GYM-018).
    if ClubMembership.objects.filter(club=club, student_id=student_id).exists():
        raise ConflictError("You have already applied for membership in this club.")

    try:
        with transaction.atomic():
            return ClubMembership.objects.create(
                club=club,
                student_id=student_id,
                description=description.strip(),
                status=MEMBERSHIP_STATUS_OPEN,
            )
    except IntegrityError as exc:
        # The same application sent twice at once passes the check above (BR-GYM-009).
        raise ConflictError("You have already applied for membership in this club.") from exc


@transaction.atomic
def approve_membership(
    *,
    membership_id: int,
    actor_id: int,
    remarks: str = "",
) -> ClubMembership:
    """Confirm an open application (UC-GYM-005, BR-GYM-011, AFR-GYM-021, AFR-GYM-022)."""
    membership = (
        reviewable_memberships(actor_id)
        .select_for_update(of=("self",))
        .select_related("club")
        .filter(id=membership_id)
        .first()
    )
    if not membership:
        raise NotFoundError(f"Membership {membership_id} not found.")

    try:
        validate_not_own_application(membership.student_id, actor_id)
    except DomainError as exc:
        raise PermissionDeniedError(str(exc), code="own_application") from exc
    try:
        new_status = transition_membership(membership.status, "APPROVE", "club_head")
    except DomainError as exc:
        raise ConflictError(str(exc)) from exc

    membership.status = new_status
    membership.remarks = remarks.strip()
    membership.approved_at = datetime.datetime.now(datetime.UTC)
    membership.approved_by_id = actor_id
    membership.save(update_fields=["status", "remarks", "approved_at", "approved_by_id"])
    return membership
