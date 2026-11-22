from django.db.models import QuerySet

from modules.gymkhana.models.club import Club, ClubLeadership
from modules.gymkhana.selectors.scoping import scope_clubs


def get_club(club_id: int) -> Club | None:
    return Club.objects.filter(id=club_id).first()


def list_clubs(user, status: str | None = None, category: str | None = None) -> QuerySet[Club]:
    qs = scope_clubs(user)
    if status:
        qs = qs.filter(status=status)
    if category:
        qs = qs.filter(category=category)
    return qs.order_by("name")


def get_club_leadership(club: Club) -> QuerySet[ClubLeadership]:
    return ClubLeadership.objects.filter(club=club, is_current=True)
