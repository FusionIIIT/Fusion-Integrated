"""gymkhana's public surface. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.gymkhana.domain import state_machine as sm
from modules.gymkhana.models import LeadershipAssignment, Membership


@dataclass(frozen=True)
class ClubAffiliationDTO:
    user_id: int
    leads: tuple[str, ...]
    member_of: tuple[str, ...]


def get_club_affiliations(user_ids: Sequence[int]) -> dict[int, ClubAffiliationDTO]:
    """Current leadership and confirmed memberships, by club name, for each person asked about."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    leads: dict[int, list[str]] = {i: [] for i in ids}
    member: dict[int, list[str]] = {i: [] for i in ids}
    for uid, name in (LeadershipAssignment.objects
                      .filter(user_id__in=ids, valid_to__isnull=True)
                      .values_list("user_id", "club__name")):
        leads[uid].append(name)
    for uid, name in (Membership.objects
                      .filter(user_id__in=ids, status=sm.CONFIRMED)
                      .values_list("user_id", "club__name")):
        member[uid].append(name)
    return {i: ClubAffiliationDTO(i, tuple(sorted(leads[i])), tuple(sorted(member[i])))
            for i in ids}
