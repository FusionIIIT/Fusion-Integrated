import pytest

from modules.gymkhana import contracts
from modules.gymkhana.models.club import Club, ClubLeadership
from modules.gymkhana.models.membership import ClubMembership

pytestmark = pytest.mark.django_db


def test_contracts_plural_queries():
    club = Club.objects.create(
        name="Art Club",
        category="Cultural",
        faculty_councillor_id=201,
        status="confirmed",
    )
    ClubLeadership.objects.create(club=club, student_id=101, role="coordinator", is_current=True)
    ClubMembership.objects.create(club=club, student_id=103, status="confirmed")

    # Contract: get_student_club_memberships
    memberships = contracts.get_student_club_memberships([103, 999])
    assert 103 in memberships
    assert len(memberships[103]) == 1
    assert memberships[103][0].club_name == "Art Club"
    assert memberships[999] == []

    # Contract: get_club_leaders
    leaders = contracts.get_club_leaders([club.id, 999])
    assert club.id in leaders
    assert len(leaders[club.id]) == 1
    assert leaders[club.id][0].student_id == 101
    assert leaders[999] == []
