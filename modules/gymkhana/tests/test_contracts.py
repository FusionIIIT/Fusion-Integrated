"""Contracts tests for Gymkhana module."""
import pytest

from modules.gymkhana.contracts import get_clubs, get_confirmed_club_members
from modules.gymkhana.models.club import Club
from modules.gymkhana.models.membership import ClubMembership

pytestmark = pytest.mark.django_db


def test_get_clubs_contract():
    c1 = Club.objects.create(
        name="Contract Club 1",
        category="technical",
        coordinator_id=1,
        co_coordinator_id=2,
        faculty_councillor_id=3,
        status="confirmed",
    )
    c2 = Club.objects.create(
        name="Contract Club 2",
        category="sports",
        coordinator_id=4,
        co_coordinator_id=5,
        faculty_councillor_id=6,
        status="open",
    )

    res = get_clubs([c1.id, c2.id, 9999])
    assert len(res) == 2
    assert res[c1.id].name == "Contract Club 1"
    assert res[c1.id].category == "technical"
    assert res[c2.id].status == "open"

    # Empty list
    assert get_clubs([]) == {}


def test_get_confirmed_club_members_contract():
    club = Club.objects.create(
        name="Contract Club 3",
        category="cultural",
        coordinator_id=1,
        co_coordinator_id=2,
        faculty_councillor_id=3,
        status="confirmed",
    )
    ClubMembership.objects.create(club=club, student_id=101, status="confirmed")
    ClubMembership.objects.create(club=club, student_id=102, status="open")

    res = get_confirmed_club_members([club.id])
    assert len(res[club.id]) == 1
    assert res[club.id][0].student_id == 101

    assert get_confirmed_club_members([]) == {}
