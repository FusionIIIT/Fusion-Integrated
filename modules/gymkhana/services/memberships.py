"""Membership services for Gymkhana."""

from __future__ import annotations

import datetime

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.gymkhana.domain.constants import (
    MEMBERSHIP_STATUS_OPEN,
)
from modules.gymkhana.domain.exceptions import DomainError
from modules.gymkhana.domain.state_machines import transition_membership
from modules.gymkhana.domain.validation import validate_club_is_confirmed
from modules.gymkhana.models.club import Club
from modules.gymkhana.models.membership import ClubMembership
from modules.gymkhana.selectors.scoping import is_club_head


@transaction.atomic
def apply_membership(*, club_id: int, student_id: int, description: str = "") -> ClubMembership:
    """Submit a membership application to a confirmed club (UC-GYM-004, BW-GYM-01)."""
    club = Club.objects.filter(id=club_id).first()
    if not club:
        raise NotFoundError(f"Club {club_id} not found.")

    try:
        validate_club_is_confirmed(club.status)
    except DomainError as exc:
        raise ConflictError(str(exc)) from exc

    if ClubMembership.objects.filter(club=club, student_id=student_id).exists():
        raise ConflictError("You have already applied for membership in this club.")

    return ClubMembership.objects.create(
        club=club,
        student_id=student_id,
        description=description.strip(),
        status=MEMBERSHIP_STATUS_OPEN,
    )


@transaction.atomic
def approve_membership(
    *,
    membership_id: int,
    actor_id: int,
    remarks: str = "",
) -> ClubMembership:
    """Approve an open membership application to confirmed status (UC-GYM-005, BW-GYM-01)."""
    membership = (
        ClubMembership.objects.select_for_update()
        .select_related("club")
        .filter(id=membership_id)
        .first()
    )
    if not membership:
        raise NotFoundError(f"Membership {membership_id} not found.")

    if not is_club_head(actor_id, membership.club):
        raise PermissionDeniedError(
            "Only the active Club Head can approve membership applications."
        )

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
