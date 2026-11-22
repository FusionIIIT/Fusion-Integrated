from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.gymkhana.models.booking import ClubBooking
from modules.gymkhana.models.budget import ClubBudgetRequest
from modules.gymkhana.models.club import Club, ClubLeadership
from modules.gymkhana.models.report import ClubEventReport

pytestmark = pytest.mark.django_db


@pytest.fixture
def test_setup():
    UserRef.objects.create(
        user_id=101, username="s101", display_name="Student Leader", kind="student",
        batch_year=2023, discipline="CSE",
    )
    UserRef.objects.create(
        user_id=102, username="s102", display_name="Co Leader", kind="student",
        batch_year=2023, discipline="CSE",
    )
    UserRef.objects.create(
        user_id=103, username="s103", display_name="General Student", kind="student",
        batch_year=2023, discipline="CSE",
    )
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

    missing = c.get("/api/v1/gymkhana/clubs/999999/")
    assert missing.status_code == 404


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

    listed = leader_client.get(
        f"/api/v1/gymkhana/clubs/{test_setup.id}/memberships/"
    )
    assert listed.status_code == 200
    assert len(listed.json()) >= 1


def test_book_session_api(stub_iam, test_setup):
    leader_client = _client(
        stub_iam,
        user_id=101,
        modules=("gymkhana",),
        permissions=(
            "gymkhana.club.view",
            "gymkhana.session.book",
            "gymkhana.budget.request",
            "gymkhana.report.review",
        ),
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


def test_confirm_leadership_and_event_api(stub_iam, test_setup):
    test_setup.status = "open"
    test_setup.save(update_fields=["status"])
    admin = _client(
        stub_iam,
        user_id=201,
        modules=("gymkhana",),
        permissions=("gymkhana.club.approve",),
    )
    confirmed = admin.post(f"/api/v1/gymkhana/clubs/{test_setup.id}/confirm/")
    assert confirmed.status_code == 200

    leader = _client(
        stub_iam,
        user_id=101,
        modules=("gymkhana",),
        permissions=("gymkhana.leadership.update", "gymkhana.event.book"),
    )
    leadership = leader.post(
        f"/api/v1/gymkhana/clubs/{test_setup.id}/leadership/",
        {"new_coordinator_id": 103, "new_co_coordinator_id": 102},
        format="json",
    )
    assert leadership.status_code == 200
    leader = _client(
        stub_iam,
        user_id=103,
        modules=("gymkhana",),
        permissions=("gymkhana.event.book",),
    )
    event = leader.post(
        f"/api/v1/gymkhana/clubs/{test_setup.id}/events/",
        {
            "title": "Literature Fest",
            "venue": "Auditorium",
            "date": str(date.today()),
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "description": "Annual fest",
        },
        format="json",
    )
    assert event.status_code == 201


def test_poll_create_and_vote_api(stub_iam, test_setup):
    leader = _client(
        stub_iam,
        user_id=101,
        modules=("gymkhana",),
        permissions=("gymkhana.poll.create", "gymkhana.poll.vote"),
    )
    created = leader.post(
        f"/api/v1/gymkhana/clubs/{test_setup.id}/polls/",
        {
            "title": "Book of the year",
            "target_batches": ["2023"],
            "target_branches": ["CSE"],
            "expires_at": "2030-01-01T12:00:00Z",
            "choices": ["One", "Two"],
        },
        format="json",
    )
    assert created.status_code == 201
    poll_id = created.json()["id"]

    student = _client(
        stub_iam,
        user_id=103,
        modules=("gymkhana",),
        permissions=("gymkhana.poll.vote",),
    )
    listed = student.get("/api/v1/gymkhana/polls/")
    assert listed.status_code == 200
    choice_id = created.json()["choices"][0]["id"]
    voted = student.post(
        f"/api/v1/gymkhana/polls/{poll_id}/vote/",
        {"choice_id": choice_id},
        format="json",
    )
    assert voted.status_code == 200


def test_club_create_booking_and_list_endpoints(stub_iam, test_setup):
    admin = _client(
        stub_iam,
        user_id=201,
        modules=("gymkhana",),
        permissions=("gymkhana.club.create", "gymkhana.club.view"),
    )
    created = admin.post(
        "/api/v1/gymkhana/clubs/",
        {
            "name": "Chess Club",
            "category": "Cultural",
            "description": "Chess",
            "coordinator_id": 101,
            "co_coordinator_id": 102,
            "faculty_councillor_id": 201,
        },
        format="json",
    )
    assert created.status_code == 201

    leader = _client(
        stub_iam,
        user_id=101,
        modules=("gymkhana",),
        permissions=(
            "gymkhana.club.view",
            "gymkhana.session.book",
            "gymkhana.budget.request",
            "gymkhana.report.review",
        ),
    )
    listed = leader.get(f"/api/v1/gymkhana/clubs/{test_setup.id}/bookings/")
    assert listed.status_code == 200

    budget = leader.post(
        f"/api/v1/gymkhana/clubs/{test_setup.id}/budgets/",
        {},
        format="json",
    )
    assert budget.status_code in (400, 403)
    missing_budget = leader.get(
        "/api/v1/gymkhana/clubs/999999/budgets/"
    )
    assert missing_budget.status_code == 404
    missing_report = leader.get(
        "/api/v1/gymkhana/clubs/999999/reports/"
    )
    assert missing_report.status_code == 404


def test_filter_validation_and_scoped_downloads(stub_iam, test_setup):
    student = _client(
        stub_iam,
        user_id=103,
        modules=("gymkhana",),
        permissions=("gymkhana.club.view",),
    )
    unknown = student.get("/api/v1/gymkhana/clubs/?unexpected=x")
    assert unknown.status_code == 400
    invalid_status = student.get("/api/v1/gymkhana/clubs/?status=broken")
    assert invalid_status.status_code == 400
    invalid_category = student.get("/api/v1/gymkhana/clubs/?category=broken")
    assert invalid_category.status_code == 400

    other = Club.objects.create(
        name="Private Open Club",
        category="Sports",
        faculty_councillor_id=201,
        status="open",
    )
    detail = student.get(f"/api/v1/gymkhana/clubs/{other.id}/")
    assert detail.status_code == 404

    booking = ClubBooking.objects.create(
        club=test_setup,
        booking_type="session",
        title="Poster",
        venue="L-101",
        date=date.today(),
        start_time="10:00",
        end_time="11:00",
        created_by_id=101,
        poster=SimpleUploadedFile("poster.pdf", b"%PDF-1.4", content_type="application/pdf"),
    )
    poster = student.get(f"/api/v1/gymkhana/bookings/{booking.id}/poster/")
    assert poster.status_code in (200, 404)

    budget = ClubBudgetRequest.objects.create(
        club=test_setup,
        amount="100.00",
        purpose="Test",
        description="Test",
        supporting_file=SimpleUploadedFile("budget.pdf", b"%PDF-1.4", content_type="application/pdf"),
        submitted_by_id=101,
    )
    head = _client(
        stub_iam,
        user_id=101,
        modules=("gymkhana",),
        permissions=("gymkhana.budget.request",),
    )
    budget_download = head.get(f"/api/v1/gymkhana/budgets/{budget.id}/file/")
    assert budget_download.status_code in (200, 404)

    report = ClubEventReport.objects.create(
        club=test_setup,
        title="Report",
        description="Test",
        student_incharge_id=103,
        event_name="Test event",
        event_datetime=timezone.now(),
        report_file=SimpleUploadedFile("report.pdf", b"%PDF-1.4", content_type="application/pdf"),
        submitted_by_id=101,
    )
    councillor = _client(
        stub_iam,
        user_id=201,
        modules=("gymkhana",),
        permissions=("gymkhana.report.review",),
    )
    report_download = councillor.get(f"/api/v1/gymkhana/reports/{report.id}/file/")
    assert report_download.status_code in (200, 404)


def test_budget_and_report_api(stub_iam, test_setup):
    leader = _client(
        stub_iam,
        user_id=101,
        modules=("gymkhana",),
        permissions=("gymkhana.budget.request", "gymkhana.report.submit"),
    )
    budget_file = SimpleUploadedFile(
        "budget.pdf", b"%PDF-1.4 test", content_type="application/pdf"
    )
    budget = leader.post(
        f"/api/v1/gymkhana/clubs/{test_setup.id}/budgets/",
        {
            "amount": "1250.50",
            "purpose": "Equipment",
            "description": "Replacement equipment",
            "supporting_file": budget_file,
        },
        format="multipart",
    )
    assert budget.status_code == 201
    budgets = leader.get(
        f"/api/v1/gymkhana/clubs/{test_setup.id}/budgets/"
    )
    assert budgets.status_code == 200

    report_file = SimpleUploadedFile(
        "report.pdf", b"%PDF-1.4 report", content_type="application/pdf"
    )
    report = leader.post(
        f"/api/v1/gymkhana/clubs/{test_setup.id}/reports/submit/",
        {
            "title": "Annual event",
            "description": "Event outcomes",
            "report_file": report_file,
            "student_incharge_id": 103,
            "event_name": "Annual event",
            "event_datetime": "2026-12-01T10:00:00Z",
        },
        format="multipart",
    )
    assert report.status_code == 201

    councillor = _client(
        stub_iam,
        user_id=201,
        modules=("gymkhana",),
        permissions=("gymkhana.report.review",),
    )
    reviewed = councillor.get(
        f"/api/v1/gymkhana/clubs/{test_setup.id}/reports/"
    )
    assert reviewed.status_code == 200
    assert len(reviewed.json()) == 1
