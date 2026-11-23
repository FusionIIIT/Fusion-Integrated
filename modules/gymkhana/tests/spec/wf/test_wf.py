# ruff: noqa: N802

import datetime

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.gymkhana.models.club import Club
from modules.gymkhana.models.membership import ClubMembership
from modules.gymkhana.models.poll import Poll, PollChoice, PollTargetGroup, PollVote

pytestmark = pytest.mark.django_db


@pytest.fixture
def wf_users():
    for uid, kind in ((101, "student"), (102, "student"), (103, "student"),
                      (104, "student"), (201, "faculty"), (999, "student")):
        UserRef.objects.create(user_id=uid, username=f"wf{uid}",
                               display_name=f"WF User {uid}", kind=kind, is_active=True)


def _client(stub_iam, uid, perms, kind="student", roles=("student",)):
    stub_iam(make_session(user_id=uid, kind=kind, roles=roles, modules=("gymkhana",),
                          permissions=perms))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token-123")
    return client


def _club(name="WF Club", status="confirmed", coordinator=101, cocoordinator=102,
          faculty=201):
    return Club.objects.create(name=name, category="technical", coordinator_id=coordinator,
                               co_coordinator_id=cocoordinator,
                               faculty_councillor_id=faculty, status=status)


def test_WF_001_BW_GYM_01_STT_Transition_1_no_membership_to_open(stub_iam, wf_users):
    """WF-001 / BW-GYM-01 STT Transition 1 — no membership to open."""
    club = _club("WF001")
    client = _client(stub_iam, 103, ("gymkhana.membership.create",))
    response = client.post("/api/v1/gymkhana/memberships/apply/",
                           {"club_id": club.id, "description": "Apply"}, format="json")
    assert response.status_code == 201
    assert response.data["status"] == "open"
    membership = ClubMembership.objects.get(id=response.data["id"])
    assert membership.status == "open"


def test_WF_002_BW_GYM_01_STT_Transition_1_guard_unconfirmed_blocks_open(stub_iam, wf_users):
    """WF-002 / BW-GYM-01 STT Transition 1 guard — unconfirmed club blocks open state."""
    club = _club("WF002", status="open")
    client = _client(stub_iam, 103, ("gymkhana.membership.create",))
    count = ClubMembership.objects.count()
    response = client.post("/api/v1/gymkhana/memberships/apply/",
                           {"club_id": club.id}, format="json")
    assert response.status_code in (400, 409)
    assert ClubMembership.objects.count() == count


def test_WF_003_BW_GYM_01_STT_Transition_2_open_to_confirmed(stub_iam, wf_users):
    """WF-003 / BW-GYM-01 STT Transition 2 — open to confirmed."""
    club = _club("WF003")
    membership = ClubMembership.objects.create(club=club, student_id=103,
                                               status="open")
    client = _client(stub_iam, 101, ("gymkhana.membership.approve",))
    response = client.post(f"/api/v1/gymkhana/memberships/{membership.id}/approve/",
                           {}, format="json")
    assert response.status_code == 200
    membership.refresh_from_db()
    assert membership.status == "confirmed"


def test_WF_004_BW_GYM_01_STT_Transition_2_guard_unauthorized_cannot_approve(stub_iam, wf_users):
    """WF-004 / BW-GYM-01 STT Transition 2 guard — unauthorized Club Head cannot approve."""
    club_a = _club("WF004A")
    _club("WF004B", coordinator=102, cocoordinator=104)
    membership = ClubMembership.objects.create(club=club_a, student_id=103,
                                               status="open")
    client = _client(stub_iam, 104, ("gymkhana.membership.approve",))
    response = client.post(f"/api/v1/gymkhana/memberships/{membership.id}/approve/",
                           {}, format="json")
    assert response.status_code in (403, 404)
    membership.refresh_from_db()
    assert membership.status == "open"


def test_WF_005_BW_GYM_01_full_path_no_membership_to_open_to_confirmed(stub_iam, wf_users):
    """WF-005 / BW-GYM-01 full path — no membership to open to confirmed."""
    club = _club("WF005")
    student = _client(stub_iam, 103, ("gymkhana.membership.create",))
    apply = student.post("/api/v1/gymkhana/memberships/apply/",
                         {"club_id": club.id}, format="json")
    assert apply.status_code == 201
    assert apply.data["status"] == "open"
    membership = ClubMembership.objects.get(id=apply.data["id"])
    head = _client(stub_iam, 101, ("gymkhana.membership.approve",))
    approve = head.post(f"/api/v1/gymkhana/memberships/{membership.id}/approve/",
                        {"remarks": "Approved"}, format="json")
    assert approve.status_code == 200
    membership.refresh_from_db()
    assert membership.status == "confirmed"


def test_WF_006_BW_GYM_02_STT_Transition_1_poll_not_available_to_open(stub_iam, wf_users):
    """WF-006 / BW-GYM-02 STT Transition 1 — poll not available to poll open."""
    club = _club("WF006")
    client = _client(stub_iam, 101, ("gymkhana.poll.view", "gymkhana.poll.create"))
    expires = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1)).isoformat()
    response = client.post("/api/v1/gymkhana/polls/", {
        "club_id": club.id, "title": "WF006", "expires_at": expires,
        "choices": ["A", "B"], "target_groups": [{"batch": "all", "branch": "all"}],
    }, format="json")
    assert response.status_code == 201
    assert response.data["status"] == "active"
    assert len(response.data["choices"]) == 2
    assert response.data["target_groups"]


def test_WF_007_BW_GYM_02_STT_Transition_1_guard_fewer_than_two_choices(stub_iam, wf_users):
    """WF-007 / BW-GYM-02 STT Transition 1 guard — fewer than two choices blocks creation."""
    club = _club("WF007")
    client = _client(stub_iam, 101, ("gymkhana.poll.view", "gymkhana.poll.create"))
    count = Poll.objects.count()
    response = client.post("/api/v1/gymkhana/polls/", {
        "club_id": club.id, "title": "WF007",
        "expires_at": (datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1)).isoformat(),
        "choices": ["A"],
    }, format="json")
    assert response.status_code == 400
    assert Poll.objects.count() == count


def test_WF_008_BW_GYM_02_STT_Transition_2_not_voted_to_vote_recorded(stub_iam, wf_users):
    """WF-008 / BW-GYM-02 STT Transition 2 — not voted to vote recorded."""
    club = _club("WF008")
    poll = Poll.objects.create(club=club, created_by_id=101, title="WF008",
                               expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1),
                               status="active")
    choice = PollChoice.objects.create(poll=poll, choice_text="A")
    PollTargetGroup.objects.create(poll=poll, batch="all", branch="all")
    client = _client(stub_iam, 103, ("gymkhana.poll.vote",))
    response = client.post(f"/api/v1/gymkhana/polls/{poll.id}/vote/",
                           {"choice_id": choice.id}, format="json")
    assert response.status_code in (200, 201)
    choice.refresh_from_db()
    assert choice.vote_count == 1
    assert PollVote.objects.filter(poll=poll, student_id=103).count() == 1


def test_WF_009_BW_GYM_02_STT_Transition_2_guard_already_voted(stub_iam, wf_users):
    """WF-009 / BW-GYM-02 STT Transition 2 guard — already voted blocks second vote."""
    club = _club("WF009")
    poll = Poll.objects.create(club=club, created_by_id=101, title="WF009",
                               expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1),
                               status="active")
    choice = PollChoice.objects.create(poll=poll, choice_text="A")
    PollVote.objects.create(poll=poll, student_id=103, choice=choice)
    client = _client(stub_iam, 103, ("gymkhana.poll.vote",))
    count = PollVote.objects.filter(poll=poll).count()
    response = client.post(f"/api/v1/gymkhana/polls/{poll.id}/vote/",
                           {"choice_id": choice.id}, format="json")
    assert response.status_code in (400, 409)
    assert PollVote.objects.filter(poll=poll).count() == count
    choice.refresh_from_db()
    assert choice.vote_count == 0


def test_WF_010_BW_GYM_02_STT_Transition_2_guard_expired_poll(stub_iam, wf_users):
    """WF-010 / BW-GYM-02 STT Transition 2 guard — expired poll blocks vote."""
    club = _club("WF010")
    poll = Poll.objects.create(club=club, created_by_id=101, title="WF010",
                               expires_at=datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1),
                               status="active")
    choice = PollChoice.objects.create(poll=poll, choice_text="A")
    PollTargetGroup.objects.create(poll=poll, batch="all", branch="all")
    client = _client(stub_iam, 103, ("gymkhana.poll.vote",))
    response = client.post(f"/api/v1/gymkhana/polls/{poll.id}/vote/",
                           {"choice_id": choice.id}, format="json")
    assert response.status_code == 400
    assert not PollVote.objects.filter(poll=poll).exists()


def test_WF_011_BW_GYM_02_full_path_poll_created_to_vote_recorded(stub_iam, wf_users):
    """WF-011 / BW-GYM-02 full path — poll created then eligible student votes."""
    club = _club("WF011")
    head = _client(stub_iam, 101, ("gymkhana.poll.view", "gymkhana.poll.create"))
    expires = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1)).isoformat()
    created = head.post("/api/v1/gymkhana/polls/", {
        "club_id": club.id, "title": "WF011", "expires_at": expires,
        "choices": ["A", "B"], "target_groups": [{"batch": "all", "branch": "all"}],
    }, format="json")
    assert created.status_code == 201
    choice_id = created.data["choices"][0]["id"]
    student = _client(stub_iam, 103, ("gymkhana.poll.vote",))
    voted = student.post(f"/api/v1/gymkhana/polls/{created.data['id']}/vote/",
                         {"choice_id": choice_id}, format="json")
    assert voted.status_code in (200, 201)
    poll = Poll.objects.get(id=created.data["id"])
    assert poll.status == "active"
    assert PollChoice.objects.get(id=choice_id).vote_count == 1


def test_WF_012_BW_GYM_03_STT_Transition_1_club_not_created_to_open(stub_iam, wf_users):
    """WF-012 / BW-GYM-03 STT Transition 1 — club not created to club open."""
    client = _client(stub_iam, 999, ("gymkhana.club.view", "gymkhana.club.create"),
                     kind="student", roles=("student_admin",))
    response = client.post("/api/v1/gymkhana/clubs/", {
        "name": "WF012", "category": "technical", "coordinator_id": 101,
        "co_coordinator_id": 102, "faculty_councillor_id": 201,
    }, format="json")
    assert response.status_code == 201
    assert response.data["status"] == "open"


def test_WF_013_BW_GYM_03_STT_Transition_1_guard_invalid_coordinator(stub_iam, wf_users):
    """WF-013 / BW-GYM-03 STT Transition 1 guard — invalid coordinator blocks club creation."""
    client = _client(stub_iam, 999, ("gymkhana.club.view", "gymkhana.club.create"),
                     kind="student", roles=("student_admin",))
    count = Club.objects.count()
    response = client.post("/api/v1/gymkhana/clubs/", {
        "name": "WF013", "category": "sports", "coordinator_id": 301,
        "co_coordinator_id": 102, "faculty_councillor_id": 201,
    }, format="json")
    assert response.status_code == 400
    assert Club.objects.count() == count


def test_WF_014_BW_GYM_03_STT_Transition_2_club_open_to_confirmed(stub_iam, wf_users):
    """WF-014 / BW-GYM-03 STT Transition 2 — club open to club confirmed."""
    club = _club("WF014", status="open")
    client = _client(stub_iam, 999, ("gymkhana.club.approve",),
                     kind="student", roles=("student_admin",))
    response = client.post(f"/api/v1/gymkhana/clubs/{club.id}/confirm/")
    assert response.status_code == 200
    club.refresh_from_db()
    assert club.status == "confirmed"


def test_WF_015_BW_GYM_03_STT_Transition_2_guard_non_admin_cannot_confirm(stub_iam, wf_users):
    """WF-015 / BW-GYM-03 STT Transition 2 guard — non-Student-Admin cannot confirm."""
    club = _club("WF015", status="open")
    client = _client(stub_iam, 101, ("gymkhana.club.approve",))
    response = client.post(f"/api/v1/gymkhana/clubs/{club.id}/confirm/")
    assert response.status_code == 403
    club.refresh_from_db()
    assert club.status == "open"


def test_WF_016_BW_GYM_03_full_path_club_not_created_to_open_to_confirmed(stub_iam, wf_users):
    """WF-016 / BW-GYM-03 full path — club not created to open to confirmed."""
    admin = _client(stub_iam, 999, ("gymkhana.club.view", "gymkhana.club.create",
                                    "gymkhana.club.approve"),
                    kind="student", roles=("student_admin",))
    created = admin.post("/api/v1/gymkhana/clubs/", {
        "name": "WF016", "category": "cultural", "coordinator_id": 101,
        "co_coordinator_id": 102, "faculty_councillor_id": 201,
    }, format="json")
    assert created.status_code == 201
    assert created.data["status"] == "open"
    confirmed = admin.post(f"/api/v1/gymkhana/clubs/{created.data['id']}/confirm/")
    assert confirmed.status_code == 200
    club = Club.objects.get(id=created.data["id"])
    assert club.status == "confirmed"
