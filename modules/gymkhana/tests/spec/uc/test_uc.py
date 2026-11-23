# ruff: noqa: N802

import datetime

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.gymkhana.models.booking import VenueBooking
from modules.gymkhana.models.budget import ClubBudgetRequest
from modules.gymkhana.models.club import Club
from modules.gymkhana.models.membership import ClubMembership
from modules.gymkhana.models.poll import Poll, PollChoice, PollVote
from modules.gymkhana.models.report import ClubEventReport

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _temp_media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")


@pytest.fixture
def uc_users():
    for user_id, kind in ((101, "student"), (102, "student"), (103, "student"),
                          (104, "student"), (201, "faculty"), (202, "faculty"),
                          (301, "staff")):
        UserRef.objects.create(user_id=user_id, username=f"uc{user_id}",
                               display_name=f"UC User {user_id}", kind=kind, is_active=True)


def _client(stub_iam, user_id, permissions, kind="student", roles=("student",)):
    stub_iam(make_session(user_id=user_id, kind=kind, roles=roles,
                          modules=("gymkhana",), permissions=permissions))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token-123")
    return client


def _club(name="UC Club", status="confirmed", faculty=201, coordinator=101, cocoord=102):
    return Club.objects.create(name=name, category="technical",
                               coordinator_id=coordinator, co_coordinator_id=cocoord,
                               faculty_councillor_id=faculty, status=status)


def test_UC_001_UC_GYM_001_Main_Flow_create_new_club(stub_iam, uc_users):
    """UC-001 / UC-GYM-001 Main Flow."""
    client = _client(stub_iam, 999, ("gymkhana.club.view", "gymkhana.club.create"),
                     roles=("student_admin",))
    response = client.post("/api/v1/gymkhana/clubs/", {
        "name": "UC001 Club", "category": "technical", "coordinator_id": 101,
        "co_coordinator_id": 102, "faculty_councillor_id": 201,
    }, format="json")
    assert response.status_code == 201
    assert response.data["status"] == "open"
    assert Club.objects.filter(id=response.data["id"], status="open").exists()


def test_UC_002_UC_GYM_001_Alternative_Flow_invalid_assignment(stub_iam, uc_users):
    """UC-002 / UC-GYM-001 Alternative Flow."""
    client = _client(stub_iam, 999, ("gymkhana.club.view", "gymkhana.club.create"),
                     roles=("student_admin",))
    count = Club.objects.count()
    response = client.post("/api/v1/gymkhana/clubs/", {
        "name": "UC002 Club", "category": "sports", "coordinator_id": 301,
        "co_coordinator_id": 102, "faculty_councillor_id": 201,
    }, format="json")
    assert response.status_code == 400
    assert Club.objects.count() == count


def test_UC_004_UC_GYM_002_Alternative_Flow_slot_conflict(stub_iam, uc_users):
    """UC-004 / UC-GYM-002 Alternative Flow."""
    club = _club("UC004")
    VenueBooking.objects.create(club=club, booking_type="session", venue="Hall 1",
                                booking_date=datetime.date(2026, 12, 10),
                                start_time=datetime.time(10), end_time=datetime.time(12),
                                booked_by_id=101)
    client = _client(stub_iam, 101, ("gymkhana.booking.create",))
    count = VenueBooking.objects.count()
    response = client.post("/api/v1/gymkhana/bookings/session/", {
        "club_id": club.id, "venue": "Hall 1", "booking_date": "2026-12-10",
        "start_time": "11:00:00", "end_time": "13:00:00",
    }, format="json")
    assert response.status_code in (400, 409)
    assert VenueBooking.objects.count() == count


def test_UC_006_UC_GYM_003_Alternative_Flow_cross_type_overlap(stub_iam, uc_users):
    """UC-006 / UC-GYM-003 Alternative Flow."""
    club = _club("UC006")
    VenueBooking.objects.create(club=club, booking_type="session", venue="Hall 1",
                                booking_date=datetime.date(2026, 12, 10),
                                start_time=datetime.time(10), end_time=datetime.time(12),
                                booked_by_id=101)
    client = _client(stub_iam, 101, ("gymkhana.booking.create",))
    count = VenueBooking.objects.count()
    response = client.post("/api/v1/gymkhana/bookings/event/", {
        "club_id": club.id, "name": "Overlap", "venue": "Hall 1",
        "booking_date": "2026-12-10", "start_time": "11:00:00", "end_time": "13:00:00",
        "faculty_councillor_id": 201,
    }, format="json")
    assert response.status_code in (400, 409)
    assert VenueBooking.objects.count() == count


def test_UC_007_UC_GYM_004_Main_Flow_apply(stub_iam, uc_users):
    """UC-007 / UC-GYM-004 Main Flow."""
    club = _club("UC007")
    client = _client(stub_iam, 103, ("gymkhana.membership.create",))
    response = client.post("/api/v1/gymkhana/memberships/apply/",
                           {"club_id": club.id, "description": "Applicant"}, format="json")
    assert response.status_code == 201
    assert response.data["status"] == "open"


def test_UC_008_UC_GYM_004_Alternative_Flow_multi_club(stub_iam, uc_users):
    """UC-008 / UC-GYM-004 Alternative Flow."""
    club_a = _club("UC008A")
    club_b = _club("UC008B")
    client = _client(stub_iam, 103, ("gymkhana.membership.create",))
    first = client.post("/api/v1/gymkhana/memberships/apply/", {"club_id": club_a.id}, format="json")
    second = client.post("/api/v1/gymkhana/memberships/apply/", {"club_id": club_b.id}, format="json")
    assert first.status_code == 201
    assert second.status_code == 201
    assert ClubMembership.objects.filter(student_id=103).count() == 2


def test_UC_009_UC_GYM_004_Exception_Flow_duplicate_rejected(stub_iam, uc_users):
    """UC-009 / UC-GYM-004 Exception Flow."""
    club = _club("UC009")
    membership = ClubMembership.objects.create(club=club, student_id=103,
                                               description="Original", status="open")
    client = _client(stub_iam, 103, ("gymkhana.membership.create",))
    response = client.post("/api/v1/gymkhana/memberships/apply/",
                           {"club_id": club.id, "description": "Duplicate"}, format="json")
    assert response.status_code in (400, 409)
    membership.refresh_from_db()
    assert membership.description == "Original"
    assert membership.status == "open"


def test_UC_010_UC_GYM_005_Main_Flow_approve_membership(stub_iam, uc_users):
    """UC-010 / UC-GYM-005 Main Flow."""
    club = _club("UC010")
    membership = ClubMembership.objects.create(club=club, student_id=103,
                                               description="Applicant", status="open")
    client = _client(stub_iam, 101, ("gymkhana.membership.approve",))
    response = client.post(f"/api/v1/gymkhana/memberships/{membership.id}/approve/",
                           {"remarks": "Welcome"}, format="json")
    assert response.status_code == 200
    membership.refresh_from_db()
    assert membership.status == "confirmed"
    assert membership.remarks == "Welcome"


def test_UC_011_UC_GYM_005_Exception_Flow_wrong_club_not_changed(stub_iam, uc_users):
    """UC-011 / UC-GYM-005 Exception Flow."""
    club_a = _club("UC011A")
    _club("UC011B", coordinator=102, cocoord=104)
    membership = ClubMembership.objects.create(club=club_a, student_id=103,
                                               description="Applicant", status="open")
    client = _client(stub_iam, 104, ("gymkhana.membership.approve",))
    # User 102 is head of Club B but not Club A.
    response = client.post(f"/api/v1/gymkhana/memberships/{membership.id}/approve/",
                           {}, format="json")
    assert response.status_code in (403, 404)
    membership.refresh_from_db()
    assert membership.status == "open"


def test_UC_013_UC_GYM_006_Exception_Flow_fewer_than_two_choices(stub_iam, uc_users):
    """UC-013 / UC-GYM-006 Exception Flow."""
    club = _club("UC013")
    client = _client(stub_iam, 101, ("gymkhana.poll.view", "gymkhana.poll.create"))
    count = Poll.objects.count()
    response = client.post("/api/v1/gymkhana/polls/", {
        "club_id": club.id, "title": "UC Poll",
        "expires_at": (datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1)).isoformat(),
        "choices": ["Only"],
    }, format="json")
    assert response.status_code == 400
    assert Poll.objects.count() == count


def test_UC_014_UC_GYM_007_Main_Flow_vote(stub_iam, uc_users):
    """UC-014 / UC-GYM-007 Main Flow."""
    club = _club("UC014")
    poll = Poll.objects.create(club=club, created_by_id=101, title="UC Vote",
                               expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1),
                               status="active")
    choice = PollChoice.objects.create(poll=poll, choice_text="A")
    from modules.gymkhana.models.poll import PollTargetGroup
    PollTargetGroup.objects.create(poll=poll, batch="all", branch="all")
    client = _client(stub_iam, 103, ("gymkhana.poll.view", "gymkhana.poll.vote"))
    detail = client.get(f"/api/v1/gymkhana/polls/{poll.id}/")
    response = client.post(f"/api/v1/gymkhana/polls/{poll.id}/vote/",
                           {"choice_id": choice.id}, format="json")
    assert detail.status_code == 200
    assert detail.data["choices"]
    assert response.status_code in (200, 201)
    choice.refresh_from_db()
    assert choice.vote_count == 1


def test_UC_015_UC_GYM_007_Exception_Flow_already_voted(stub_iam, uc_users):
    """UC-015 / UC-GYM-007 Exception Flow."""
    club = _club("UC015")
    poll = Poll.objects.create(club=club, created_by_id=101, title="UC Vote",
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


def test_UC_016_UC_GYM_008_Main_Flow_change_leadership(stub_iam, uc_users):
    """UC-016 / UC-GYM-008 Main Flow."""
    club = _club("UC016")
    client = _client(stub_iam, 101, ("gymkhana.club.manage",))
    response = client.post(f"/api/v1/gymkhana/clubs/{club.id}/leadership/",
                           {"coordinator_id": 103, "co_coordinator_id": 104}, format="json")
    assert response.status_code == 200
    club.refresh_from_db()
    assert club.coordinator_id == 103
    assert club.co_coordinator_id == 104


def test_UC_017_UC_GYM_008_Exception_Flow_unauthorized_preserves_leadership(stub_iam, uc_users):
    """UC-017 / UC-GYM-008 Exception Flow."""
    club = _club("UC017")
    client = _client(stub_iam, 103, ("gymkhana.club.manage",))
    response = client.post(f"/api/v1/gymkhana/clubs/{club.id}/leadership/",
                           {"coordinator_id": 103, "co_coordinator_id": 104}, format="json")
    assert response.status_code == 403
    club.refresh_from_db()
    assert (club.coordinator_id, club.co_coordinator_id) == (101, 102)


def test_UC_018_UC_GYM_009_Main_Flow_submit_budget(stub_iam, uc_users):
    """UC-018 / UC-GYM-009 Main Flow."""
    club = _club("UC018")
    client = _client(stub_iam, 101, ("gymkhana.budget.view", "gymkhana.budget.create"))
    file = SimpleUploadedFile("budget.pdf", b"Budget", content_type="application/pdf")
    response = client.post("/api/v1/gymkhana/budgets/", {
        "club_id": club.id, "amount": "100.00", "purpose": "Equipment",
        "description": "Replacement", "supporting_file": file,
    }, format="multipart")
    assert response.status_code == 201
    assert response.data["status"] == "open"


def test_UC_019_UC_GYM_009_Exception_Flow_negative_or_missing_file(stub_iam, uc_users):
    """UC-019 / UC-GYM-009 Exception Flow."""
    club = _club("UC019")
    client = _client(stub_iam, 101, ("gymkhana.budget.view", "gymkhana.budget.create"))
    count = ClubBudgetRequest.objects.count()
    negative = client.post("/api/v1/gymkhana/budgets/", {
        "club_id": club.id, "amount": "-100.00", "purpose": "Invalid",
    }, format="multipart")
    missing = client.post("/api/v1/gymkhana/budgets/", {
        "club_id": club.id, "amount": "100.00", "purpose": "Missing",
    }, format="multipart")
    assert negative.status_code == 400
    assert missing.status_code == 400
    assert ClubBudgetRequest.objects.count() == count


def test_UC_020_UC_GYM_010_Main_Flow_submit_report(stub_iam, uc_users):
    """UC-020 / UC-GYM-010 Main Flow."""
    club = _club("UC020")
    client = _client(stub_iam, 101, ("gymkhana.report.view", "gymkhana.report.create"))
    file = SimpleUploadedFile("report.pdf", b"Report", content_type="application/pdf")
    response = client.post("/api/v1/gymkhana/reports/", {
        "club_id": club.id, "student_incharge_id": 103, "event_name": "UC Event",
        "event_date": "2026-11-20T18:00:00Z", "description": "Report",
        "report_file": file,
    }, format="multipart")
    assert response.status_code == 201
    assert ClubEventReport.objects.filter(id=response.data["id"]).exists()


def test_UC_021_UC_GYM_010_Exception_Flow_missing_report_file(stub_iam, uc_users):
    """UC-021 / UC-GYM-010 Exception Flow."""
    club = _club("UC021")
    client = _client(stub_iam, 101, ("gymkhana.report.view", "gymkhana.report.create"))
    count = ClubEventReport.objects.count()
    response = client.post("/api/v1/gymkhana/reports/", {
        "club_id": club.id, "student_incharge_id": 103, "event_name": "Missing",
        "event_date": "2026-11-20T18:00:00Z",
    }, format="multipart")
    assert response.status_code == 400
    assert ClubEventReport.objects.count() == count


def test_UC_022_UC_GYM_011_Main_Flow_approve_club(stub_iam, uc_users):
    """UC-022 / UC-GYM-011 Main Flow."""
    club = _club("UC022", status="open")
    client = _client(stub_iam, 999, ("gymkhana.club.approve",), roles=("student_admin",))
    response = client.post(f"/api/v1/gymkhana/clubs/{club.id}/confirm/")
    assert response.status_code == 200
    club.refresh_from_db()
    assert club.status == "confirmed"


def test_UC_023_UC_GYM_011_Exception_Flow_confirmed_club_fails(stub_iam, uc_users):
    """UC-023 / UC-GYM-011 Exception Flow."""
    club = _club("UC023", status="confirmed")
    client = _client(stub_iam, 999, ("gymkhana.club.approve",), roles=("student_admin",))
    response = client.post(f"/api/v1/gymkhana/clubs/{club.id}/confirm/")
    assert response.status_code in (400, 409)
    club.refresh_from_db()
    assert club.status == "confirmed"


def test_UC_024_UC_GYM_012_Main_Flow_assigned_faculty_reviews_report(stub_iam, uc_users):
    """UC-024 / UC-GYM-012 Main Flow."""
    club = _club("UC024")
    report = ClubEventReport.objects.create(club=club, submitted_by_id=101,
                                             student_incharge_id=103, event_name="UC Report",
                                             event_date=datetime.datetime.now(datetime.UTC))
    client = _client(stub_iam, 201, ("gymkhana.report.view",),
                     kind="faculty", roles=("faculty",))
    response = client.get(f"/api/v1/gymkhana/reports/?club_id={club.id}")
    detail = client.get(f"/api/v1/gymkhana/reports/{report.id}/")
    assert response.status_code == 200
    assert response.data["results"]
    assert detail.status_code == 200


def test_UC_025_UC_GYM_012_Exception_Flow_unassigned_faculty_denied(stub_iam, uc_users):
    """UC-025 / UC-GYM-012 Exception Flow."""
    club = _club("UC025")
    report = ClubEventReport.objects.create(club=club, submitted_by_id=101,
                                             student_incharge_id=103, event_name="Private",
                                             event_date=datetime.datetime.now(datetime.UTC))
    client = _client(stub_iam, 202, ("gymkhana.report.view",),
                     kind="faculty", roles=("faculty",))
    response = client.get(f"/api/v1/gymkhana/reports/?club_id={club.id}")
    detail = client.get(f"/api/v1/gymkhana/reports/{report.id}/")
    assert response.status_code in (403, 404, 200)
    if response.status_code == 200:
        assert report.id not in [item["id"] for item in response.data["results"]]
    assert detail.status_code in (403, 404)
