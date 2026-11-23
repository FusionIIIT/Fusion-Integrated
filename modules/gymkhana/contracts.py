from collections.abc import Sequence
from dataclasses import dataclass

from modules.gymkhana.models.club import ClubLeadership
from modules.gymkhana.models.membership import ClubMembership


@dataclass(frozen=True)
class StudentClubMembershipDTO:
    student_id: int
    club_id: int
    club_name: str
    status: str


def get_student_club_memberships(
    student_ids: Sequence[int],
) -> dict[int, list[StudentClubMembershipDTO]]:
    ids = {int(i) for i in student_ids if i is not None}
    if not ids:
        return {}
    rows = (
        ClubMembership.objects.filter(student_id__in=ids)
        .select_related("club")
        .values("student_id", "club_id", "club__name", "status")
    )
    result: dict[int, list[StudentClubMembershipDTO]] = {uid: [] for uid in ids}
    for r in rows:
        dto = StudentClubMembershipDTO(
            student_id=r["student_id"],
            club_id=r["club_id"],
            club_name=r["club__name"],
            status=r["status"],
        )
        result[r["student_id"]].append(dto)
    return result


@dataclass(frozen=True)
class ClubLeadershipDTO:
    club_id: int
    club_name: str
    role: str
    student_id: int


def get_club_leaders(club_ids: Sequence[int]) -> dict[int, list[ClubLeadershipDTO]]:
    ids = {int(i) for i in club_ids if i is not None}
    if not ids:
        return {}
    rows = (
        ClubLeadership.objects.filter(club_id__in=ids, is_current=True)
        .select_related("club")
        .values("club_id", "club__name", "role", "student_id")
    )
    result: dict[int, list[ClubLeadershipDTO]] = {cid: [] for cid in ids}
    for r in rows:
        dto = ClubLeadershipDTO(
            club_id=r["club_id"],
            club_name=r["club__name"],
            role=r["role"],
            student_id=r["student_id"],
        )
        result[r["club_id"]].append(dto)
    return result
