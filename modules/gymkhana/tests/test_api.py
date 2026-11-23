"""API endpoint and authorization tests for Gymkhana."""
import datetime

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.gymkhana.models.club import Club
from modules.gymkhana.models.poll import Poll
from modules.gymkhana.tasks import expire_polls

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _temp_media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")


def _as(stub_iam, uid, perms, kind="student", roles=("student",)):
    stub_iam(
        make_session(
            user_id=uid,
            kind=kind,
            roles=roles,
            modules=("gymkhana",),
            permissions=perms,
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token-123")
    return client


@pytest.fixture
def test_setup():
    # Student leaders
    UserRef.objects.create(user_id=101, username="stu101", display_name="Student 101", kind="student", is_active=True)
    UserRef.objects.create(user_id=102, username="stu102", display_name="Student 102", kind="student", is_active=True)
    UserRef.objects.create(user_id=103, username="stu103", display_name="Student 103", kind="student", is_active=True)
    UserRef.objects.create(user_id=104, username="stu104", display_name="Student 104", kind="student", is_active=True)
    # Faculty councillor
    UserRef.objects.create(user_id=201, username="fac201", display_name="Faculty 201", kind="faculty", is_active=True)

    return Club.objects.create(
        name="Music Club",
        category="cultural",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
        status="confirmed",
    )


def test_student_admin_creates_and_approves_club(stub_iam, test_setup):
    admin_perms = (
        "gymkhana.club.view",
        "gymkhana.club.create",
        "gymkhana.club.approve",
    )
    client = _as(stub_iam, 999, admin_perms, kind="student", roles=("student_admin",))

    # 1. Create club
    res = client.post(
        "/api/v1/gymkhana/clubs/",
        {
            "name": "Chess Club",
            "category": "sports",
            "description": "Mind sport",
            "coordinator_id": 101,
            "co_coordinator_id": 102,
            "faculty_councillor_id": 201,
        },
        format="json",
    )
    assert res.status_code == 201
    club_id = res.data["id"]
    assert res.data["status"] == "open"

    # 2. Confirm club
    conf_res = client.post(f"/api/v1/gymkhana/clubs/{club_id}/confirm/")
    assert conf_res.status_code == 200
    assert conf_res.data["status"] == "confirmed"

    # 3. List clubs
    list_res = client.get("/api/v1/gymkhana/clubs/")
    assert list_res.status_code == 200
    assert len(list_res.data["results"]) >= 2

    # 4. Detail view
    detail_res = client.get(f"/api/v1/gymkhana/clubs/{club_id}/")
    assert detail_res.status_code == 200
    assert detail_res.data["name"] == "Chess Club"


def test_club_leadership_change_api(stub_iam, test_setup):
    club = test_setup
    head_client = _as(stub_iam, 101, ("gymkhana.club.manage",))

    res = head_client.post(
        f"/api/v1/gymkhana/clubs/{club.id}/leadership/",
        {"coordinator_id": 103, "co_coordinator_id": 104},
        format="json",
    )
    assert res.status_code == 200
    assert res.data["coordinator_id"] == 103
    assert res.data["co_coordinator_id"] == 104


def test_bookings_api(stub_iam, test_setup):
    club = test_setup
    head_client = _as(stub_iam, 101, ("gymkhana.booking.view", "gymkhana.booking.create"))

    # Session booking
    sess_res = head_client.post(
        "/api/v1/gymkhana/bookings/session/",
        {
            "club_id": club.id,
            "venue": "Hall 1",
            "booking_date": "2026-12-15",
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "name": "Jam Session",
            "description": "Band rehearsal",
        },
        format="json",
    )
    assert sess_res.status_code == 201
    booking_id = sess_res.data["id"]

    # Event booking
    ev_res = head_client.post(
        "/api/v1/gymkhana/bookings/event/",
        {
            "club_id": club.id,
            "venue": "Hall 2",
            "booking_date": "2026-12-15",
            "start_time": "14:00:00",
            "end_time": "16:00:00",
            "name": "Winter Concert",
            "description": "Live musical performance",
            "faculty_councillor_id": 201,
        },
        format="json",
    )
    assert ev_res.status_code == 201

    # List bookings
    list_res = head_client.get("/api/v1/gymkhana/bookings/")
    assert list_res.status_code == 200
    assert len(list_res.data["results"]) >= 2

    # Detail booking
    det_res = head_client.get(f"/api/v1/gymkhana/bookings/{booking_id}/")
    assert det_res.status_code == 200
    assert det_res.data["venue"] == "Hall 1"


def test_membership_apply_and_approve_api(stub_iam, test_setup):
    club = test_setup
    student_client = _as(stub_iam, 103, ("gymkhana.membership.view", "gymkhana.membership.create"))

    # Apply
    res = student_client.post(
        "/api/v1/gymkhana/memberships/apply/",
        {"club_id": club.id, "description": "Violinist"},
        format="json",
    )
    assert res.status_code == 201
    mem_id = res.data["id"]

    # Student lists own memberships
    m_list = student_client.get("/api/v1/gymkhana/memberships/")
    assert m_list.status_code == 200
    assert len(m_list.data["results"]) == 1

    # Head approves
    head_client = _as(stub_iam, 101, ("gymkhana.membership.view", "gymkhana.membership.approve"))
    app_res = head_client.post(
        f"/api/v1/gymkhana/memberships/{mem_id}/approve/",
        {"remarks": "Approved"},
        format="json",
    )
    assert app_res.status_code == 200
    assert app_res.data["status"] == "confirmed"


def test_poll_lifecycle_api(stub_iam, test_setup):
    club = test_setup
    head_client = _as(stub_iam, 101, ("gymkhana.poll.view", "gymkhana.poll.create", "gymkhana.poll.vote"))

    # Create poll via API
    future = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=2)).isoformat()
    create_res = head_client.post(
        "/api/v1/gymkhana/polls/",
        {
            "club_id": club.id,
            "title": "Band Lead",
            "description": "Vote for leader",
            "expires_at": future,
            "choices": ["Alice", "Bob"],
            "target_groups": [{"batch": "all", "branch": "all"}],
        },
        format="json",
    )
    assert create_res.status_code == 201
    poll_id = create_res.data["id"]

    # List polls
    list_res = head_client.get("/api/v1/gymkhana/polls/")
    assert list_res.status_code == 200

    # Detail poll
    det_res = head_client.get(f"/api/v1/gymkhana/polls/{poll_id}/")
    assert det_res.status_code == 200
    choice_id = det_res.data["choices"][0]["id"]

    # Vote
    student_client = _as(stub_iam, 103, ("gymkhana.poll.view", "gymkhana.poll.vote"))
    vote_res = student_client.post(f"/api/v1/gymkhana/polls/{poll_id}/vote/", {"choice_id": choice_id}, format="json")
    assert vote_res.status_code == 200


def test_budget_requests_api(stub_iam, test_setup):
    club = test_setup
    head_client = _as(stub_iam, 101, ("gymkhana.budget.view", "gymkhana.budget.create"))

    dummy_file = SimpleUploadedFile("bill.pdf", b"Dummy budget data", content_type="application/pdf")
    res = head_client.post(
        "/api/v1/gymkhana/budgets/",
        {
            "club_id": club.id,
            "amount": "2500.00",
            "purpose": "Audio Cables",
            "description": "Quarterly equipment renewal",
            "supporting_file": dummy_file,
        },
        format="multipart",
    )
    assert res.status_code == 201
    budget_id = res.data["id"]

    # List budgets
    list_res = head_client.get("/api/v1/gymkhana/budgets/")
    assert list_res.status_code == 200

    # Detail budget
    det_res = head_client.get(f"/api/v1/gymkhana/budgets/{budget_id}/")
    assert det_res.status_code == 200
    assert det_res.data["purpose"] == "Audio Cables"


def test_event_reports_api(stub_iam, test_setup):
    club = test_setup
    head_client = _as(stub_iam, 101, ("gymkhana.report.view", "gymkhana.report.create"))

    dummy_file = SimpleUploadedFile("report.pdf", b"Content", content_type="application/pdf")
    res = head_client.post(
        "/api/v1/gymkhana/reports/",
        {
            "club_id": club.id,
            "student_incharge_id": 102,
            "event_name": "Autumn Fest",
            "event_date": "2026-11-20T18:00:00Z",
            "description": "Fest documentation",
            "report_file": dummy_file,
        },
        format="multipart",
    )
    assert res.status_code == 201
    report_id = res.data["id"]

    # Assigned Faculty Councillor (user_id=201) reviews report
    councillor_client = _as(stub_iam, 201, ("gymkhana.report.view",), kind="faculty", roles=("faculty",))
    list_res = councillor_client.get(f"/api/v1/gymkhana/reports/?club_id={club.id}")
    assert list_res.status_code == 200
    assert len(list_res.data["results"]) == 1

    det_res = councillor_client.get(f"/api/v1/gymkhana/reports/{report_id}/")
    assert det_res.status_code == 200
    assert det_res.data["event_name"] == "Autumn Fest"


def test_celery_expire_polls_task(test_setup):
    club = test_setup
    past = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1)
    poll = Poll.objects.create(
        club=club,
        created_by_id=101,
        title="Old Poll",
        expires_at=past,
        status="active",
    )
    count = expire_polls()
    assert count >= 1
    poll.refresh_from_db()
    assert poll.status == "expired"
