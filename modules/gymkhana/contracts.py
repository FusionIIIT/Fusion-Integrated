"""Public surface for Gymkhana module. Plural signatures only."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.gymkhana.models.club import Club
from modules.gymkhana.models.membership import ClubMembership


@dataclass(frozen=True)
class ClubDTO:
    id: int
    name: str
    category: str
    description: str
    coordinator_id: int
    co_coordinator_id: int
    faculty_councillor_id: int
    status: str


@dataclass(frozen=True)
class ClubMemberDTO:
    club_id: int
    student_id: int
    status: str


def get_clubs(club_ids: Sequence[int]) -> dict[int, ClubDTO]:
    """Return public details for requested club IDs."""
    ids = {int(i) for i in club_ids if i is not None}
    if not ids:
        return {}
    return {
        c.id: ClubDTO(
            id=c.id,
            name=c.name,
            category=c.category,
            description=c.description,
            coordinator_id=c.coordinator_id,
            co_coordinator_id=c.co_coordinator_id,
            faculty_councillor_id=c.faculty_councillor_id,
            status=c.status,
        )
        for c in Club.objects.filter(id__in=ids)
    }


def get_confirmed_club_members(club_ids: Sequence[int]) -> dict[int, list[ClubMemberDTO]]:
    """Return confirmed membership records mapped by club ID."""
    ids = {int(i) for i in club_ids if i is not None}
    if not ids:
        return {}
    res: dict[int, list[ClubMemberDTO]] = {cid: [] for cid in ids}
    rows = ClubMembership.objects.filter(club_id__in=ids, status="confirmed")
    for r in rows:
        res[r.club_id].append(
            ClubMemberDTO(
                club_id=r.club_id,
                student_id=r.student_id,
                status=r.status,
            )
        )
    return res
