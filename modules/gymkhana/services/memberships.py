from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.gymkhana.domain.constants import STATUS_CONFIRMED, STATUS_OPEN
from modules.gymkhana.domain.state_machine import transition_membership
from modules.gymkhana.models.club import Club
from modules.gymkhana.models.membership import ClubMembership
from modules.gymkhana.selectors.scoping import is_club_head


@transaction.atomic
def apply_membership(*, club_id: int, student_id: int, remarks: str = "") -> ClubMembership:
    club = Club.objects.filter(id=club_id).first()
    if not club:
        raise NotFoundError("Club not found.", code="club_not_found")

    if club.status != STATUS_CONFIRMED:
        raise ConflictError(
            "A student may apply for membership only in a confirmed club.",
            code="club_not_confirmed",
        )

    if ClubMembership.objects.filter(club=club, student_id=student_id).exists():
        raise ConflictError(
            "A student may not submit a duplicate membership application to the same club.",
            code="duplicate_membership_application",
        )

    return ClubMembership.objects.create(
        club=club,
        student_id=student_id,
        status=STATUS_OPEN,
        remarks=remarks,
    )


@transaction.atomic
def approve_membership(
    *,
    membership_id: int,
    acting_user_id: int,
    remarks: str = "",
) -> ClubMembership:
    membership = ClubMembership.objects.select_for_update().filter(id=membership_id).first()
    if not membership:
        raise NotFoundError("Membership application not found.", code="membership_not_found")

    if not is_club_head(acting_user_id, membership.club_id):
        raise PermissionDeniedError(
            "Only the applicable club coordinator or co-coordinator may approve memberships.",
            code="not_club_head",
        )

    try:
        new_status = transition_membership(membership.status, "approve")
    except ValueError as e:
        raise ConflictError(str(e), code="illegal_membership_transition") from e

    membership.status = new_status
    if remarks:
        membership.remarks = remarks
    membership.confirmed_at = timezone.now()
    membership.save(update_fields=["status", "remarks", "confirmed_at", "updated_at"])
    return membership
