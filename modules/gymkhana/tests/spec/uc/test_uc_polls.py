# ruff: noqa: N802
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.gymkhana.models.club import Club, ClubLeadership
from modules.gymkhana.models.membership import ClubMembership
from modules.gymkhana.models.poll import PollChoice, PollVote, VotingPoll

pytestmark = pytest.mark.django_db


@pytest.fixture
def gymkhana_users():
    for user_id, kind in ((101, "student"), (102, "student"), (103, "student"), (201, "faculty")):
        UserRef.objects.create(
            user_id=user_id,
            username=f"u{user_id}",
            display_name=f"User {user_id}",
            kind=kind,
            discipline="CSE" if kind == "student" else "",
            batch_year=2023 if kind == "student" else None,
        )
    return 101, 102, 103, 201


@pytest.fixture
def confirmed_club(gymkhana_users):
    club = Club.objects.create(
        name="Literature Club",
        category="Cultural",
        description="Books",
        faculty_councillor_id=201,
        status="confirmed",
    )
    ClubLeadership.objects.create(club=club, student_id=101, role="coordinator", is_current=True)
    ClubLeadership.objects.create(club=club, student_id=102, role="co_coordinator", is_current=True)
    return club


def client_for(stub_iam, user_id, permissions=(), kind="student"):
    stub_iam(make_session(user_id=user_id, kind=kind, modules=("gymkhana",), permissions=tuple(permissions)))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock_token")
    return client


def test_TC_GYM_023_UC_GYM_005_Exception_E1_Application_No_Longer_Open(stub_iam, confirmed_club):
    """TC-GYM-023; source_id: UC-GYM-005 Exception E1 Application No Longer Open"""
    membership = ClubMembership.objects.create(club=confirmed_club, student_id=103, status="confirmed")
    leader = client_for(stub_iam, 101, ("gymkhana.membership.approve",))
    response = leader.post(
        f"/api/v1/gymkhana/memberships/{membership.id}/approve/",
        {"remarks": "Again"},
        format="json",
    )
    assert response.status_code == 409
    membership.refresh_from_db()
    assert membership.status == "confirmed"


def test_TC_GYM_024_UC_GYM_005_Exception_E1_Wrong_Club(stub_iam, confirmed_club):
    """TC-GYM-024; source_id: UC-GYM-005 Exception E1 Wrong Club"""
    other = Club.objects.create(name="Other Club", category="Sports", faculty_councillor_id=201, status="confirmed")
    ClubLeadership.objects.create(club=other, student_id=102, role="coordinator", is_current=True)
    membership = ClubMembership.objects.create(club=other, student_id=103, status="open")
    wrong_head = client_for(stub_iam, 101, ("gymkhana.membership.approve",))
    response = wrong_head.post(
        f"/api/v1/gymkhana/memberships/{membership.id}/approve/",
        {"remarks": ""},
        format="json",
    )
    assert response.status_code == 403
    membership.refresh_from_db()
    assert membership.status == "open"


def test_TC_GYM_025_UC_GYM_006_Main_Success_Flow(stub_iam, confirmed_club):
    """TC-GYM-025; source_id: UC-GYM-006 Main Success Flow"""
    leader = client_for(stub_iam, 101, ("gymkhana.poll.create",))
    response = leader.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/polls/",
        {
            "title": "Book of the Year",
            "description": "Choose",
            "target_batches": ["2023"],
            "target_branches": ["CSE"],
            "expires_at": "2030-01-01T12:00:00Z",
            "choices": ["One", "Two"],
        },
        format="json",
    )
    assert response.status_code == 201
    poll = VotingPoll.objects.get(club=confirmed_club)
    assert poll.choices.count() == 2
    assert poll.target_batches == ["2023"]
    assert poll.target_branches == ["CSE"]


def test_TC_GYM_026_UC_GYM_006_Alternative_A1(stub_iam, confirmed_club):
    """TC-GYM-026; source_id: UC-GYM-006 Alternative A1"""
    leader = client_for(stub_iam, 101, ("gymkhana.poll.create",))
    response = leader.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/polls/",
        {
            "title": "All Branches",
            "target_batches": ["2023"],
            "target_branches": ["CSE", "ECE", "ME"],
            "expires_at": "2030-01-01T12:00:00Z",
            "choices": ["Yes", "No"],
        },
        format="json",
    )
    assert response.status_code == 201
    poll = VotingPoll.objects.get(title="All Branches")
    assert set(poll.target_branches) == {"CSE", "ECE", "ME"}


def test_TC_GYM_027_UC_GYM_006_Exception_E1_Fewer_Than_Two_Choices(stub_iam, confirmed_club):
    """TC-GYM-027; source_id: UC-GYM-006 Exception E1 Fewer Than Two Choices"""
    leader = client_for(stub_iam, 101, ("gymkhana.poll.create",))
    before = VotingPoll.objects.count()
    response = leader.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/polls/",
        {
            "title": "Invalid Poll",
            "target_batches": ["2023"],
            "target_branches": ["CSE"],
            "expires_at": "2030-01-01T12:00:00Z",
            "choices": ["Only"],
        },
        format="json",
    )
    assert response.status_code == 400
    assert VotingPoll.objects.count() == before


def test_TC_GYM_028_UC_GYM_006_Exception_E1_Invalid_Target(stub_iam, confirmed_club):
    """TC-GYM-028; source_id: UC-GYM-006 Exception E1 Invalid Target"""
    leader = client_for(stub_iam, 101, ("gymkhana.poll.create",))
    before = VotingPoll.objects.count()
    response = leader.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/polls/",
        {
            "title": "Invalid Target",
            "target_batches": [],
            "target_branches": [],
            "expires_at": "2030-01-01T12:00:00Z",
            "choices": ["One", "Two"],
        },
        format="json",
    )
    assert response.status_code == 400
    assert VotingPoll.objects.count() == before


def test_TC_GYM_029_UC_GYM_007_Main_Success_Flow(stub_iam, confirmed_club):
    """TC-GYM-029; source_id: UC-GYM-007 Main Success Flow"""
    poll = VotingPoll.objects.create(
        club=confirmed_club,
        title="Active",
        target_batches=["2023"],
        target_branches=["CSE"],
        expires_at=timezone.now() + timedelta(days=1),
        created_by_id=101,
    )
    choice = PollChoice.objects.create(poll=poll, text="Choice A", votes_count=0)
    student = client_for(stub_iam, 103, ("gymkhana.poll.vote",))
    response = student.post(
        f"/api/v1/gymkhana/polls/{poll.id}/vote/",
        {"choice_id": choice.id},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "vote_recorded"
    assert PollVote.objects.filter(poll=poll, student_id=103).count() == 1
    choice.refresh_from_db()
    assert choice.votes_count == 1


def test_TC_GYM_030_UC_GYM_007_Exception_E1_Already_Voted(stub_iam, confirmed_club):
    """TC-GYM-030; source_id: UC-GYM-007 Exception E1 Already Voted"""
    poll = VotingPoll.objects.create(
        club=confirmed_club,
        title="Duplicate",
        target_batches=["2023"],
        target_branches=["CSE"],
        expires_at=timezone.now() + timedelta(days=1),
        created_by_id=101,
    )
    choice = PollChoice.objects.create(poll=poll, text="Choice", votes_count=1)
    PollVote.objects.create(poll=poll, choice=choice, student_id=103)
    student = client_for(stub_iam, 103, ("gymkhana.poll.vote",))
    response = student.post(
        f"/api/v1/gymkhana/polls/{poll.id}/vote/",
        {"choice_id": choice.id},
        format="json",
    )
    assert response.status_code == 409
    assert PollVote.objects.filter(poll=poll, student_id=103).count() == 1
    choice.refresh_from_db()
    assert choice.votes_count == 1


def test_TC_GYM_031_UC_GYM_007_Exception_E1_Student_Not_Eligible(stub_iam, confirmed_club):
    """TC-GYM-031; source_id: UC-GYM-007 Exception E1 Student Not Eligible"""
    poll = VotingPoll.objects.create(
        club=confirmed_club,
        title="Targeted",
        target_batches=["2024"],
        target_branches=["ECE"],
        expires_at=timezone.now() + timedelta(days=1),
        created_by_id=101,
    )
    choice = PollChoice.objects.create(poll=poll, text="Choice", votes_count=0)
    student = client_for(stub_iam, 103, ("gymkhana.poll.vote",))
    response = student.post(
        f"/api/v1/gymkhana/polls/{poll.id}/vote/",
        {"choice_id": choice.id},
        format="json",
    )
    assert response.status_code == 403
    assert not PollVote.objects.filter(poll=poll, student_id=103).exists()
    choice.refresh_from_db()
    assert choice.votes_count == 0


def test_TC_GYM_032_UC_GYM_007_Exception_E1_Poll_Not_Active(stub_iam, confirmed_club):
    """TC-GYM-032; source_id: UC-GYM-007 Exception E1 Poll Not Active"""
    poll = VotingPoll.objects.create(
        club=confirmed_club,
        title="Expired",
        target_batches=["2023"],
        target_branches=["CSE"],
        expires_at=timezone.now() - timedelta(days=1),
        created_by_id=101,
    )
    choice = PollChoice.objects.create(poll=poll, text="Choice", votes_count=0)
    student = client_for(stub_iam, 103, ("gymkhana.poll.vote",))
    response = student.post(
        f"/api/v1/gymkhana/polls/{poll.id}/vote/",
        {"choice_id": choice.id},
        format="json",
    )
    assert response.status_code == 409
    assert not PollVote.objects.filter(poll=poll, student_id=103).exists()
    choice.refresh_from_db()
    assert choice.votes_count == 0
