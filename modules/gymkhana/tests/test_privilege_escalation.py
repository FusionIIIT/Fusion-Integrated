import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.gymkhana.models.club import Club, ClubLeadership

pytestmark = pytest.mark.django_db


@pytest.fixture
def club():
    UserRef.objects.create(user_id=101, username="s101", display_name="Student Leader", kind="student")
    UserRef.objects.create(user_id=102, username="s102", display_name="General Student", kind="student")
    c = Club.objects.create(
        name="Chess Club",
        category="Sports",
        faculty_councillor_id=201,
        status="open",
    )
    ClubLeadership.objects.create(club=c, student_id=101, role="coordinator", is_current=True)
    return c


def _client(stub_iam, **kw):
    stub_iam(make_session(**kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token mock_token")
    return c


def test_cannot_create_club_without_permission(stub_iam):
    c = _client(
        stub_iam,
        user_id=102,
        modules=("gymkhana",),
        permissions=("gymkhana.club.view",),
    )
    res = c.post(
        "/api/v1/gymkhana/clubs/",
        {
            "name": "Unauthorized Club",
            "category": "Sports",
            "coordinator_id": 101,
            "co_coordinator_id": 102,
            "faculty_councillor_id": 201,
        },
        format="json",
    )
    assert res.status_code == 403


def test_cannot_confirm_club_without_permission(stub_iam, club):
    c = _client(
        stub_iam,
        user_id=101,
        modules=("gymkhana",),
        permissions=("gymkhana.club.view",),
    )
    res = c.post(f"/api/v1/gymkhana/clubs/{club.id}/confirm/")
    assert res.status_code == 403


def test_cannot_book_session_without_permission(stub_iam, club):
    c = _client(
        stub_iam,
        user_id=102,
        modules=("gymkhana",),
        permissions=("gymkhana.club.view",),
    )
    res = c.post(
        f"/api/v1/gymkhana/clubs/{club.id}/sessions/",
        {
            "title": "Match",
            "venue": "CC1",
            "date": "2026-12-01",
            "start_time": "10:00:00",
            "end_time": "12:00:00",
        },
        format="json",
    )
    assert res.status_code == 403


@pytest.mark.parametrize(
    "path,method",
    [
        ("/api/v1/gymkhana/clubs/", "get"),
        ("/api/v1/gymkhana/clubs/", "post"),
        ("/api/v1/gymkhana/polls/", "get"),
        ("/api/v1/gymkhana/memberships/1/approve/", "post"),
        ("/api/v1/gymkhana/clubs/1/sessions/", "post"),
        ("/api/v1/gymkhana/clubs/1/events/", "post"),
        ("/api/v1/gymkhana/clubs/1/polls/", "post"),
        ("/api/v1/gymkhana/clubs/1/budgets/", "post"),
        ("/api/v1/gymkhana/clubs/1/reports/submit/", "post"),
    ],
)
def test_every_endpoint_refuses_ungranted_module(path, method, stub_iam):
    c = _client(stub_iam, user_id=102, modules=(), permissions=())
    response = getattr(c, method)(path, {}, format="json") if method == "post" else getattr(c, method)(path)
    assert response.status_code in (401, 403)
