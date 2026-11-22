"""Reads about clubs beyond scope: current leaders, batched."""
from __future__ import annotations

from collections.abc import Sequence

from modules.gymkhana.domain import state_machine as sm
from modules.gymkhana.models import Membership
from modules.gymkhana.selectors.scoping import current_leaders


def leaders_by_club(club_ids: Sequence[int]) -> dict[int, dict[str, int]]:
    """{club_id: {role: user_id}} for current leadership, one query for any number of clubs."""
    out: dict[int, dict[str, int]] = {}
    rows = current_leaders().filter(club_id__in=list(club_ids)).values_list(
        "club_id", "role", "user_id")
    for club_id, role, user_id in rows:
        out.setdefault(club_id, {})[role] = user_id
    return out


def confirmed_member_ids(club_id: int) -> list[int]:
    return sorted(Membership.objects.filter(club_id=club_id, status=sm.CONFIRMED)
                  .values_list("user_id", flat=True))


def own_membership_status(user_id: int, club_ids: Sequence[int]) -> dict[int, str]:
    return dict(Membership.objects.filter(user_id=user_id, club_id__in=list(club_ids))
                .values_list("club_id", "status"))
