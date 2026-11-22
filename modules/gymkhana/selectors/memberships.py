from django.db.models import QuerySet

from modules.gymkhana.models.club import Club
from modules.gymkhana.models.membership import ClubMembership
from modules.gymkhana.selectors.scoping import scope_memberships


def get_membership(membership_id: int) -> ClubMembership | None:
    return ClubMembership.objects.filter(id=membership_id).first()


def list_memberships(user, club: Club, status: str | None = None) -> QuerySet[ClubMembership]:
    qs = scope_memberships(user, club)
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-created_at")
