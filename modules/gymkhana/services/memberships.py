"""Membership services (UC-GYM-004, UC-GYM-005, BW-GYM-01)."""
from __future__ import annotations

from django.db import IntegrityError, transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.gymkhana.domain.state_machine import ClubMembershipStateMachine
from modules.gymkhana.models import Club, ClubMembership


def apply_membership(*, club: Club, student_id: int) -> ClubMembership:
    """Submit membership application for confirmed club (UC-GYM-004, BR-GYM-007, BR-GYM-009)."""
    if club.status != "confirmed":
        raise ConflictError(
            "Membership applications are only permitted for confirmed clubs.",
            code="club_not_confirmed",
        )

    initial_status = ClubMembershipStateMachine.transition(
        None, "apply", "student", guards={"club_is_confirmed": True}
    )

    try:
        with transaction.atomic():
            return ClubMembership.objects.create(
                club=club,
                student_id=student_id,
                status=initial_status,
            )
    except IntegrityError as exc:
        raise ConflictError(
            "You have already applied for membership in this club.",
            code="duplicate_membership_application",
        ) from exc


def approve_membership(*, membership_id: int, actor_user_id: int) -> ClubMembership:
    """Approve an open club membership to confirmed (UC-GYM-005, BR-GYM-010, BR-GYM-011)."""
    with transaction.atomic():
        try:
            membership = (
                ClubMembership.objects.select_for_update()
                .select_related("club")
                .get(pk=membership_id)
            )
        except ClubMembership.DoesNotExist as exc:
            raise NotFoundError(
                f"Membership application {membership_id} not found.",
                code="membership_not_found",
            ) from exc

        if actor_user_id not in (membership.club.coordinator_id, membership.club.co_coordinator_id):
            raise ConflictError(
                "Only the applicable club coordinator or co-coordinator may approve memberships.",
                code="not_club_head",
            )

        new_status = ClubMembershipStateMachine.transition(
            membership.status,
            "approve",
            "club_head",
            guards={"actor_is_club_head": True},
        )
        membership.status = new_status
        membership.save(update_fields=["status", "updated_at"])
        return membership
