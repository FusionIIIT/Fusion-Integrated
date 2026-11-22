"""Gymkhana public contract. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class ClubLeadersDTO:
    club_id: int
    club_name: str
    coordinator_id: int
    co_coordinator_id: int
    faculty_councillor_id: int
    status: str


@dataclass(frozen=True)
class StudentClubMembershipDTO:
    club_id: int
    club_name: str
    status: str  # 'open', 'confirmed'


def get_active_club_leaders(
    club_ids: Sequence[int],
) -> dict[int, ClubLeadersDTO]:
    """Return leadership assignments for requested club IDs."""
    ids = {int(i) for i in club_ids if i is not None}
    if not ids:
        return {}
    from modules.gymkhana.models import Club

    rows = Club.objects.filter(pk__in=ids)
    return {
        c.pk: ClubLeadersDTO(
            club_id=c.pk,
            club_name=c.name,
            coordinator_id=c.coordinator_id,
            co_coordinator_id=c.co_coordinator_id,
            faculty_councillor_id=c.faculty_councillor_id,
            status=c.status,
        )
        for c in rows
    }


def get_student_memberships(
    user_ids: Sequence[int],
) -> dict[int, list[StudentClubMembershipDTO]]:
    """Return club memberships for a batch of student IDs."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    from modules.gymkhana.models import ClubMembership

    rows = (
        ClubMembership.objects.filter(student_id__in=ids)
        .select_related("club")
        .values_list("student_id", "club_id", "club__name", "status")
    )
    result: dict[int, list[StudentClubMembershipDTO]] = {
        uid: [] for uid in ids
    }
    for uid, cid, cname, status in rows:
        result[uid].append(StudentClubMembershipDTO(cid, cname, status))
    return result
