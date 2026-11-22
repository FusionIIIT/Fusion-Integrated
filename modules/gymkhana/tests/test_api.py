from datetime import date

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.gymkhana.models.club import Club, ClubLeadership

pytestmark = pytest.mark.django_db


@pytest.fixture
def test_setup():
    UserRef.objects.create(user_id=101, username="s101", display_name="Student Leader", kind="student")
    UserRef.objects.create(user_id=102, username="s102", display_name="Co Leader", kind="student")
    UserRef.objects.create(user_id=103, username="s103", display_name="General Student", kind="student")
    UserRef.objects.create(user_id=201, username="f201", display_name="Faculty Councillor", kind="faculty")

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


def _client(stub_iam, **kw):
    stub_iam(make_session(**kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token mock_token")
    return c


def test_list_and_detail_clubs(stub_iam, test_setup):
    c = _client(
        stub_iam,
        user_id=103,
        modules=("gymkhana",),
        permissions=("gymkhana.club.view",),
    )
    res = c.get("/api/v1/gymkhana/clubs/")
    assert res.status_code == 200
    assert len(res.json()) >= 1

    detail_res = c.get(f"/api/v1/gymkhana/clubs/{test_setup.id}/")
    assert detail_res.status_code == 200
    assert detail_res.json()["name"] == "Literature Club"


def test_apply_and_approve_membership_api(stub_iam, test_setup):
    student_client = _client(
        stub_iam,
        user_id=103,
        modules=("gymkhana",),
        permissions=("gymkhana.club.view", "gymkhana.membership.apply"),
    )
    res = student_client.post(
        f"/api/v1/gymkhana/clubs/{test_setup.id}/memberships/apply/",
        {"remarks": "Eager reader"},
        format="json",
    )
    assert res.status_code == 201
    membership_id = res.json()["id"]

    # Leader approves
    leader_client = _client(
        stub_iam,
        user_id=101,
        modules=("gymkhana",),
        permissions=("gymkhana.club.view", "gymkhana.membership.approve"),
    )
    approve_res = leader_client.post(
        f"/api/v1/gymkhana/memberships/{membership_id}/approve/",
        {"remarks": "Welcome!"},
        format="json",
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "confirmed"


def test_book_session_api(stub_iam, test_setup):
    leader_client = _client(
        stub_iam,
        user_id=101,
        modules=("gymkhana",),
        permissions=("gymkhana.club.view", "gymkhana.session.book"),
    )
    res = leader_client.post(
        f"/api/v1/gymkhana/clubs/{test_setup.id}/sessions/",
        {
            "title": "Book Discussion",
            "venue": "L-101",
            "date": str(date.today()),
            "start_time": "15:00:00",
            "end_time": "17:00:00",
            "description": "Discussing 1984",
        },
        format="json",
    )
    assert res.status_code == 201
    assert res.json()["venue"] == "L-101"
