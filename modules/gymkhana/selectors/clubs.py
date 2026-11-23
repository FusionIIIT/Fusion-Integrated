"""Club read selectors for Gymkhana."""

from __future__ import annotations

from collections.abc import Sequence

from django.db.models import QuerySet

from core.api.exceptions import NotFoundError
from modules.gymkhana.models.club import Club, ClubLeadershipHistory


def get_club_by_id(club_id: int) -> Club:
    """Return club by ID or raise NotFound (404)."""
    club = Club.objects.filter(id=club_id).first()
    if not club:
        raise NotFoundError(f"Club {club_id} not found.")
    return club


def get_clubs_by_ids(club_ids: Sequence[int]) -> QuerySet[Club]:
    """Return clubs for plural contract."""
    return Club.objects.filter(id__in=club_ids)


def get_leadership_history(club_id: int) -> QuerySet[ClubLeadershipHistory]:
    """Return leadership change history for a club."""
    return ClubLeadershipHistory.objects.filter(club_id=club_id).order_by("-changed_at")
