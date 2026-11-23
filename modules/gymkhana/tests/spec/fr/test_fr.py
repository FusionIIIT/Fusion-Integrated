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
from modules.gymkhana.models.notification import GymkhanaNotification
from modules.gymkhana.models.poll import Poll, PollChoice, PollVote
from modules.gymkhana.models.report import ClubEventReport

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _temp_media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")


@pytest.fixture
def gymkhana_users():
    for user_id, kind in (
        (101, "student"),
        (102, "student"),
        (103, "student"),
        (104, "student"),
        (201, "faculty"),
        (202, "faculty"),
        (301, "staff"),
    ):
        UserRef.objects.create(
            user_id=user_id,
            username=f"user{user_id}",
            display_name=f"User {user_id}",
            kind=kind,
            is_active=True,
        )


def _client(stub_iam, user_id, permissions, kind="student", roles=("student",)):
    stub_iam(
        make_session(
            user_id=user_id,
            kind=kind,
            roles=roles,
            modules=("gymkhana",),
            permissions=permissions,
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token-123")
    return client


def _club(**kwargs):
    return Club.objects.create(
        name=kwargs.pop("name", "Robotics Club"),
        category=kwargs.pop("category", "technical"),
        coordinator_id=kwargs.pop("coordinator_id", 101),
        co_coordinator_id=kwargs.pop("co_coordinator_id", 102),
        faculty_councillor_id=kwargs.pop("faculty_councillor_id", 201),
        status=kwargs.pop("status", "confirmed"),
        **kwargs,
    )


def test_FR_001_CFR_GYM_001_AFR_GYM_001_create_club_happy_path(
    stub_iam, gymkhana_users
):
    """FR-001 / CFR-GYM-001 / AFR-GYM-001."""
    client = _client(
        stub_iam, 999, ("gymkhana.club.view", "gymkhana.club.create"),
        roles=("student_admin",),
    )
    response = client.post(
        "/api/v1/gymkhana/clubs/",
        {
            "name": "Chess Club",
            "category": "technical",
            "coordinator_id": 101,
            "co_coordinator_id": 102,
            "faculty_councillor_id": 201,
            "description": "Chess",
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.data["status"] == "open"
    assert Club.objects.filter(id=response.data["id"], status="open").exists()


def test_FR_002_CFR_GYM_001_AFR_GYM_002_invalid_coordinator_rejected(
    stub_iam, gymkhana_users
):
    """FR-002 / CFR-GYM-001 / AFR-GYM-002."""
    client = _client(
        stub_iam,
        999,
        ("gymkhana.club.view", "gymkhana.club.create"),
        roles=("student_admin",),
    )
    count = Club.objects.count()
    response = client.post(
        "/api/v1/gymkhana/clubs/",
        {
            "name": "Invalid Club",
            "category": "technical",
            "coordinator_id": 301,
            "co_coordinator_id": 102,
            "faculty_councillor_id": 201,
        },
        format="json",
    )
    assert response.status_code == 400
    assert Club.objects.count() == count


def test_FR_003_CFR_GYM_001_AFR_GYM_003_invalid_faculty_rejected(
    stub_iam, gymkhana_users
):
    """FR-003 / CFR-GYM-001 / AFR-GYM-003."""
    client = _client(
        stub_iam,
        999,
        ("gymkhana.club.view", "gymkhana.club.create"),
        roles=("student_admin",),
    )
    count = Club.objects.count()
    response = client.post(
        "/api/v1/gymkhana/clubs/",
        {
            "name": "Invalid Faculty Club",
            "category": "sports",
            "coordinator_id": 101,
            "co_coordinator_id": 102,
            "faculty_councillor_id": 103,
        },
        format="json",
    )
    assert response.status_code == 400
    assert Club.objects.count() == count


def test_FR_004_CFR_GYM_001_AFR_GYM_004_disallowed_category_rejected(
    stub_iam, gymkhana_users
):
    """FR-004 / CFR-GYM-001 / AFR-GYM-004."""
    client = _client(
        stub_iam,
        999,
        ("gymkhana.club.view", "gymkhana.club.create"),
        roles=("student_admin",),
    )
    count = Club.objects.count()
    response = client.post(
        "/api/v1/gymkhana/clubs/",
        {
            "name": "Arts Club",
            "category": "arts",
            "coordinator_id": 101,
            "co_coordinator_id": 102,
            "faculty_councillor_id": 201,
        },
        format="json",
    )
    assert response.status_code == 400
    assert Club.objects.count() == count


def test_FR_005_CFR_GYM_001_AFR_GYM_005_new_club_open_status(
    stub_iam, gymkhana_users
):
    """FR-005 / CFR-GYM-001 / AFR-GYM-005."""
    client = _client(
        stub_iam,
        999,
        ("gymkhana.club.view", "gymkhana.club.create"),
        roles=("student_admin",),
    )
    response = client.post(
        "/api/v1/gymkhana/clubs/",
        {
            "name": "Open Status Club",
            "category": "cultural",
            "coordinator_id": 101,
            "co_coordinator_id": 102,
            "faculty_councillor_id": 201,
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.data["status"] == "open"
    club = Club.objects.get(id=response.data["id"])
    assert club.status == "open"


def test_FR_006_CFR_GYM_001_AFR_GYM_006_confirm_open_club(
    stub_iam, gymkhana_users
):
    """FR-006 / CFR-GYM-001 / AFR-GYM-006."""
    club = _club(status="open")
    client = _client(
        stub_iam,
        999,
        ("gymkhana.club.approve",),
        roles=("student_admin",),
    )
    response = client.post(f"/api/v1/gymkhana/clubs/{club.id}/confirm/")
    assert response.status_code == 200
    club.refresh_from_db()
    assert response.data["status"] == "confirmed"
    assert club.status == "confirmed"


def test_FR_007_CFR_GYM_002_AFR_GYM_007_club_head_changes_leadership(
    stub_iam, gymkhana_users
):
    """FR-007 / CFR-GYM-002 / AFR-GYM-007."""
    club = _club()
    client = _client(stub_iam, 101, ("gymkhana.club.manage",))
    response = client.post(
        f"/api/v1/gymkhana/clubs/{club.id}/leadership/",
        {"coordinator_id": 103, "co_coordinator_id": 104},
        format="json",
    )
    assert response.status_code == 200
    club.refresh_from_db()
    assert club.coordinator_id == 103
    assert club.co_coordinator_id == 104


def test_FR_008_CFR_GYM_002_AFR_GYM_008_invalid_replacement_rejected(
    stub_iam, gymkhana_users
):
    """FR-008 / CFR-GYM-002 / AFR-GYM-008."""
    club = _club()
    client = _client(stub_iam, 101, ("gymkhana.club.manage",))
    response = client.post(
        f"/api/v1/gymkhana/clubs/{club.id}/leadership/",
        {"coordinator_id": 301, "co_coordinator_id": 104},
        format="json",
    )
    assert response.status_code == 400
    club.refresh_from_db()
    assert club.coordinator_id == 101
    assert club.co_coordinator_id == 102


def test_FR_009_CFR_GYM_002_AFR_GYM_009_only_new_leadership_retained(
    stub_iam, gymkhana_users
):
    """FR-009 / CFR-GYM-002 / AFR-GYM-009."""
    club = _club()
    client = _client(stub_iam, 101, ("gymkhana.club.manage",))
    response = client.post(
        f"/api/v1/gymkhana/clubs/{club.id}/leadership/",
        {"coordinator_id": 103, "co_coordinator_id": 104},
        format="json",
    )
    assert response.status_code == 200
    club.refresh_from_db()
    assert club.coordinator_id == 103
    assert club.co_coordinator_id == 104
    assert (club.coordinator_id, club.co_coordinator_id) != (101, 102)


def test_FR_010_CFR_GYM_003_AFR_GYM_010_club_head_books_session(
    stub_iam, gymkhana_users
):
    """FR-010 / CFR-GYM-003 / AFR-GYM-010."""
    club = _club()
    client = _client(stub_iam, 101, ("gymkhana.booking.create",))
    response = client.post(
        "/api/v1/gymkhana/bookings/session/",
        {
            "club_id": club.id,
            "venue": "Hall 1",
            "booking_date": "2026-12-15",
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "name": "Session",
            "description": "Practice",
        },
        format="json",
    )
    assert response.status_code == 201
    assert VenueBooking.objects.filter(id=response.data["id"], club=club).exists()


def test_FR_011_CFR_GYM_003_AFR_GYM_011_invalid_time_range_rejected(
    stub_iam, gymkhana_users
):
    """FR-011 / CFR-GYM-003 / AFR-GYM-011."""
    club = _club()
    client = _client(stub_iam, 101, ("gymkhana.booking.create",))
    count = VenueBooking.objects.count()
    response = client.post(
        "/api/v1/gymkhana/bookings/session/",
        {
            "club_id": club.id,
            "venue": "Hall 1",
            "booking_date": "2026-12-15",
            "start_time": "12:00:00",
            "end_time": "10:00:00",
            "description": "Invalid",
        },
        format="json",
    )
    assert response.status_code == 400
    assert VenueBooking.objects.count() == count


def test_FR_012_CFR_GYM_003_AFR_GYM_012_overlapping_session_rejected(
    stub_iam, gymkhana_users
):
    """FR-012 / CFR-GYM-003 / AFR-GYM-012."""
    club = _club()
    VenueBooking.objects.create(
        club=club,
        booking_type="session",
        venue="Hall 1",
        booking_date=datetime.date(2026, 12, 15),
        start_time=datetime.time(10),
        end_time=datetime.time(12),
        booked_by_id=101,
    )
    client = _client(stub_iam, 101, ("gymkhana.booking.create",))
    count = VenueBooking.objects.count()
    response = client.post(
        "/api/v1/gymkhana/bookings/session/",
        {
            "club_id": club.id,
            "venue": "Hall 1",
            "booking_date": "2026-12-15",
            "start_time": "11:00:00",
            "end_time": "13:00:00",
            "description": "Overlap",
        },
        format="json",
    )
    assert response.status_code in (400, 409)
    assert VenueBooking.objects.count() == count


def test_FR_013_CFR_GYM_003_AFR_GYM_012_session_event_overlap_rejected(
    stub_iam, gymkhana_users
):
    """FR-013 / CFR-GYM-003 / AFR-GYM-012."""
    club = _club()
    VenueBooking.objects.create(
        club=club,
        booking_type="event",
        venue="Hall 1",
        booking_date=datetime.date(2026, 12, 15),
        start_time=datetime.time(10),
        end_time=datetime.time(12),
        faculty_councillor_id=201,
        booked_by_id=101,
    )
    client = _client(stub_iam, 101, ("gymkhana.booking.create",))
    count = VenueBooking.objects.count()
    response = client.post(
        "/api/v1/gymkhana/bookings/session/",
        {
            "club_id": club.id,
            "venue": "Hall 1",
            "booking_date": "2026-12-15",
            "start_time": "11:00:00",
            "end_time": "13:00:00",
            "description": "Overlap",
        },
        format="json",
    )
    assert response.status_code in (400, 409)
    assert VenueBooking.objects.count() == count


def test_FR_014_CFR_GYM_003_AFR_GYM_013_session_booking_queues_notification(
    stub_iam, gymkhana_users
):
    """FR-014 / CFR-GYM-003 / AFR-GYM-013."""
    club = _club()
    client = _client(stub_iam, 101, ("gymkhana.booking.create",))
    response = client.post(
        "/api/v1/gymkhana/bookings/session/",
        {
            "club_id": club.id,
            "venue": "Hall 1",
            "booking_date": "2026-12-15",
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "name": "Session",
            "description": "Practice",
        },
        format="json",
    )
    assert response.status_code == 201
    queued = GymkhanaNotification.objects.get()
    assert (queued.topic, queued.status) == ("session.booked", "pending")
    assert queued.audience == {"members_of": club.id}


def test_FR_015_CFR_GYM_003_AFR_GYM_014_club_head_books_event(
    stub_iam, gymkhana_users
):
    """FR-015 / CFR-GYM-003 / AFR-GYM-014."""
    club = _club()
    client = _client(stub_iam, 101, ("gymkhana.booking.create",))
    response = client.post(
        "/api/v1/gymkhana/bookings/event/",
        {
            "club_id": club.id,
            "venue": "Hall 2",
            "booking_date": "2026-12-16",
            "start_time": "14:00:00",
            "end_time": "16:00:00",
            "name": "Annual Event",
            "description": "Event",
            "faculty_councillor_id": 201,
        },
        format="json",
    )
    assert response.status_code == 201
    assert VenueBooking.objects.filter(id=response.data["id"], booking_type="event").exists()


def test_FR_016_CFR_GYM_003_AFR_GYM_015_event_booking_queues_notification(
    stub_iam, gymkhana_users
):
    """FR-016 / CFR-GYM-003 / AFR-GYM-015."""
    club = _club()
    client = _client(stub_iam, 101, ("gymkhana.booking.create",))
    response = client.post(
        "/api/v1/gymkhana/bookings/event/",
        {
            "club_id": club.id,
            "venue": "Hall 2",
            "booking_date": "2026-12-16",
            "start_time": "14:00:00",
            "end_time": "16:00:00",
            "name": "Annual Event",
            "description": "Event",
            "faculty_councillor_id": 201,
        },
        format="json",
    )
    assert response.status_code == 201
    queued = GymkhanaNotification.objects.get()
    assert (queued.topic, queued.status) == ("event.booked", "pending")
    assert queued.audience == {"members_of": club.id}


def test_FR_017_CFR_GYM_004_AFR_GYM_016_student_applies_confirmed_club(
    stub_iam, gymkhana_users
):
    """FR-017 / CFR-GYM-004 / AFR-GYM-016."""
    club = _club()
    client = _client(
        stub_iam, 103, ("gymkhana.membership.create", "gymkhana.membership.view")
    )
    response = client.post(
        "/api/v1/gymkhana/memberships/apply/",
        {"club_id": club.id, "description": "Violinist"},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["status"] == "open"


def test_FR_018_CFR_GYM_004_AFR_GYM_016_open_club_application_rejected(
    stub_iam, gymkhana_users
):
    """FR-018 / CFR-GYM-004 / AFR-GYM-016."""
    club = _club(status="open")
    client = _client(stub_iam, 103, ("gymkhana.membership.create",))
    count = ClubMembership.objects.count()
    response = client.post(
        "/api/v1/gymkhana/memberships/apply/",
        {"club_id": club.id, "description": "Application"},
        format="json",
    )
    assert response.status_code in (400, 409)
    assert ClubMembership.objects.count() == count


def test_FR_019_CFR_GYM_004_AFR_GYM_017_multiple_different_club_applications(
    stub_iam, gymkhana_users
):
    """FR-019 / CFR-GYM-004 / AFR-GYM-017."""
    club_a = _club(name="Club A")
    club_b = _club(name="Club B")
    client = _client(stub_iam, 103, ("gymkhana.membership.create",))
    first = client.post(
        "/api/v1/gymkhana/memberships/apply/",
        {"club_id": club_a.id},
        format="json",
    )
    second = client.post(
        "/api/v1/gymkhana/memberships/apply/",
        {"club_id": club_b.id},
        format="json",
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert ClubMembership.objects.filter(student_id=103).count() == 2


def test_FR_020_CFR_GYM_004_AFR_GYM_018_duplicate_application_rejected(
    stub_iam, gymkhana_users
):
    """FR-020 / CFR-GYM-004 / AFR-GYM-018."""
    club = _club()
    ClubMembership.objects.create(
        club=club, student_id=103, description="Existing", status="open"
    )
    client = _client(stub_iam, 103, ("gymkhana.membership.create",))
    count = ClubMembership.objects.count()
    response = client.post(
        "/api/v1/gymkhana/memberships/apply/",
        {"club_id": club.id, "description": "Duplicate"},
        format="json",
    )
    assert response.status_code in (400, 409)
    assert ClubMembership.objects.count() == count
    assert ClubMembership.objects.get(club=club, student_id=103).description == "Existing"


def test_FR_021_CFR_GYM_004_AFR_GYM_019_application_stored_open(
    stub_iam, gymkhana_users
):
    """FR-021 / CFR-GYM-004 / AFR-GYM-019."""
    club = _club()
    client = _client(stub_iam, 103, ("gymkhana.membership.create",))
    response = client.post(
        "/api/v1/gymkhana/memberships/apply/",
        {"club_id": club.id, "description": "Applicant"},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["status"] == "open"
    assert ClubMembership.objects.get(id=response.data["id"]).status == "open"


def test_FR_022_CFR_GYM_004_AFR_GYM_020_club_head_views_pending_applications(
    stub_iam, gymkhana_users
):
    """FR-022 / CFR-GYM-004 / AFR-GYM-020."""
    club = _club()
    ClubMembership.objects.create(
        club=club, student_id=103, description="Pending", status="open"
    )
    client = _client(stub_iam, 101, ("gymkhana.membership.view",))
    response = client.get(f"/api/v1/gymkhana/memberships/?club_id={club.id}")
    assert response.status_code == 200
    assert any(item["id"] for item in response.data["results"])


def test_FR_023_CFR_GYM_004_AFR_GYM_021_club_head_approves_with_remarks(
    stub_iam, gymkhana_users
):
    """FR-023 / CFR-GYM-004 / AFR-GYM-021."""
    club = _club()
    membership = ClubMembership.objects.create(
        club=club, student_id=103, description="Applicant", status="open"
    )
    client = _client(stub_iam, 101, ("gymkhana.membership.approve",))
    response = client.post(
        f"/api/v1/gymkhana/memberships/{membership.id}/approve/",
        {"remarks": "Welcome"},
        format="json",
    )
    assert response.status_code == 200
    membership.refresh_from_db()
    assert membership.status == "confirmed"
    assert membership.remarks == "Welcome"


def test_FR_024_CFR_GYM_004_AFR_GYM_022_approved_membership_confirmed(
    stub_iam, gymkhana_users
):
    """FR-024 / CFR-GYM-004 / AFR-GYM-022."""
    club = _club()
    membership = ClubMembership.objects.create(
        club=club, student_id=103, description="Applicant", status="open"
    )
    client = _client(stub_iam, 101, ("gymkhana.membership.approve",))
    response = client.post(
        f"/api/v1/gymkhana/memberships/{membership.id}/approve/",
        {},
        format="json",
    )
    assert response.status_code == 200
    membership.refresh_from_db()
    assert membership.status == "confirmed"


def test_FR_025_CFR_GYM_005_AFR_GYM_023_club_head_creates_poll(
    stub_iam, gymkhana_users
):
    """FR-025 / CFR-GYM-005 / AFR-GYM-023."""
    club = _club()
    client = _client(stub_iam, 101, ("gymkhana.poll.view", "gymkhana.poll.create"))
    expires_at = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=2)).isoformat()
    response = client.post(
        "/api/v1/gymkhana/polls/",
        {
            "club_id": club.id,
            "title": "Captain",
            "description": "Vote",
            "expires_at": expires_at,
            "choices": ["Alice", "Bob"],
            "target_groups": [{"batch": "all", "branch": "all"}],
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.data["status"] == "active"


def test_FR_026_CFR_GYM_005_AFR_GYM_024_fewer_than_two_choices_rejected(
    stub_iam, gymkhana_users
):
    """FR-026 / CFR-GYM-005 / AFR-GYM-024."""
    club = _club()
    client = _client(stub_iam, 101, ("gymkhana.poll.view", "gymkhana.poll.create"))
    count = Poll.objects.count()
    response = client.post(
        "/api/v1/gymkhana/polls/",
        {
            "club_id": club.id,
            "title": "Single choice",
            "expires_at": (
                datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1)
            ).isoformat(),
            "choices": ["Only"],
        },
        format="json",
    )
    assert response.status_code == 400
    assert Poll.objects.count() == count


def test_FR_027_CFR_GYM_005_AFR_GYM_025_poll_creation_queues_notification(
    stub_iam, gymkhana_users
):
    """FR-027 / CFR-GYM-005 / AFR-GYM-025."""
    club = _club()
    client = _client(stub_iam, 101, ("gymkhana.poll.view", "gymkhana.poll.create"))
    response = client.post(
        "/api/v1/gymkhana/polls/",
        {
            "club_id": club.id,
            "title": "Captain",
            "description": "Vote",
            "expires_at": (
                datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=2)
            ).isoformat(),
            "choices": ["Alice", "Bob"],
            "target_groups": [{"batch": "2024", "branch": "CSE"}],
        },
        format="json",
    )
    assert response.status_code == 201
    queued = GymkhanaNotification.objects.get()
    assert (queued.topic, queued.status) == ("poll.created", "pending")
    assert queued.audience == {"targets_of": response.data["id"]}


def test_FR_028_CFR_GYM_005_AFR_GYM_026_eligible_student_accesses_active_poll(
    stub_iam, gymkhana_users
):
    """FR-028 / CFR-GYM-005 / AFR-GYM-026."""
    club = _club()
    poll = Poll.objects.create(
        club=club,
        created_by_id=101,
        title="Election",
        expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1),
        status="active",
    )
    PollChoice.objects.create(poll=poll, choice_text="Alice")
    from modules.gymkhana.models.poll import PollTargetGroup

    PollTargetGroup.objects.create(poll=poll, batch="all", branch="all")
    client = _client(stub_iam, 103, ("gymkhana.poll.view",))
    response = client.get(f"/api/v1/gymkhana/polls/{poll.id}/")
    assert response.status_code == 200
    assert response.data["choices"]


def test_FR_029_CFR_GYM_005_AFR_GYM_027_eligible_student_casts_vote(
    stub_iam, gymkhana_users
):
    """FR-029 / CFR-GYM-005 / AFR-GYM-027."""
    club = _club()
    poll = Poll.objects.create(
        club=club,
        created_by_id=101,
        title="Election",
        expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1),
        status="active",
    )
    choice = PollChoice.objects.create(poll=poll, choice_text="Alice")
    client = _client(
        stub_iam, 103, ("gymkhana.poll.view", "gymkhana.poll.vote")
    )
    response = client.post(
        f"/api/v1/gymkhana/polls/{poll.id}/vote/",
        {"choice_id": choice.id},
        format="json",
    )
    assert response.status_code in (200, 201)
    choice.refresh_from_db()
    assert choice.vote_count == 1


def test_FR_030_CFR_GYM_005_AFR_GYM_028_duplicate_vote_rejected(
    stub_iam, gymkhana_users
):
    """FR-030 / CFR-GYM-005 / AFR-GYM-028."""
    club = _club()
    poll = Poll.objects.create(
        club=club,
        created_by_id=101,
        title="Election",
        expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1),
        status="active",
    )
    choice = PollChoice.objects.create(poll=poll, choice_text="Alice")
    PollVote.objects.create(poll=poll, student_id=103, choice=choice)
    client = _client(stub_iam, 103, ("gymkhana.poll.vote",))
    response = client.post(
        f"/api/v1/gymkhana/polls/{poll.id}/vote/",
        {"choice_id": choice.id},
        format="json",
    )
    assert response.status_code in (400, 409)
    choice.refresh_from_db()
    assert choice.vote_count == 0
    assert PollVote.objects.filter(poll=poll, student_id=103).count() == 1


def test_FR_031_CFR_GYM_005_AFR_GYM_028_tally_incremented_atomically(
    stub_iam, gymkhana_users
):
    """FR-031 / CFR-GYM-005 / AFR-GYM-028."""
    club = _club()
    poll = Poll.objects.create(
        club=club,
        created_by_id=101,
        title="Election",
        expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1),
        status="active",
    )
    choice = PollChoice.objects.create(poll=poll, choice_text="Alice", vote_count=0)
    other = PollChoice.objects.create(poll=poll, choice_text="Bob", vote_count=0)
    client = _client(stub_iam, 103, ("gymkhana.poll.vote",))
    response = client.post(
        f"/api/v1/gymkhana/polls/{poll.id}/vote/",
        {"choice_id": choice.id},
        format="json",
    )
    assert response.status_code in (200, 201)
    choice.refresh_from_db()
    other.refresh_from_db()
    assert choice.vote_count == 1
    assert other.vote_count == 0


def test_FR_032_CFR_GYM_006_AFR_GYM_029_submit_budget_request(
    stub_iam, gymkhana_users
):
    """FR-032 / CFR-GYM-006 / AFR-GYM-029."""
    club = _club()
    client = _client(stub_iam, 101, ("gymkhana.budget.view", "gymkhana.budget.create"))
    file = SimpleUploadedFile("budget.pdf", b"Budget", content_type="application/pdf")
    response = client.post(
        "/api/v1/gymkhana/budgets/",
        {
            "club_id": club.id,
            "amount": "2500.00",
            "purpose": "Equipment",
            "description": "Renewal",
            "supporting_file": file,
        },
        format="multipart",
    )
    assert response.status_code == 201
    assert ClubBudgetRequest.objects.filter(id=response.data["id"], status="open").exists()


def test_FR_033_CFR_GYM_006_AFR_GYM_030_negative_budget_rejected(
    stub_iam, gymkhana_users
):
    """FR-033 / CFR-GYM-006 / AFR-GYM-030."""
    club = _club()
    client = _client(stub_iam, 101, ("gymkhana.budget.view", "gymkhana.budget.create"))
    file = SimpleUploadedFile("budget.pdf", b"Budget", content_type="application/pdf")
    count = ClubBudgetRequest.objects.count()
    response = client.post(
        "/api/v1/gymkhana/budgets/",
        {
            "club_id": club.id,
            "amount": "-1.00",
            "purpose": "Invalid",
            "supporting_file": file,
        },
        format="multipart",
    )
    assert response.status_code == 400
    assert ClubBudgetRequest.objects.count() == count


def test_FR_034_CFR_GYM_006_AFR_GYM_030_missing_supporting_file_rejected(
    stub_iam, gymkhana_users
):
    """FR-034 / CFR-GYM-006 / AFR-GYM-030."""
    club = _club()
    client = _client(stub_iam, 101, ("gymkhana.budget.view", "gymkhana.budget.create"))
    count = ClubBudgetRequest.objects.count()
    response = client.post(
        "/api/v1/gymkhana/budgets/",
        {
            "club_id": club.id,
            "amount": "100.00",
            "purpose": "Missing file",
        },
        format="multipart",
    )
    assert response.status_code == 400
    assert ClubBudgetRequest.objects.count() == count


def test_FR_035_CFR_GYM_006_AFR_GYM_031_budget_stays_open_no_status_transition(
    stub_iam, gymkhana_users
):
    """FR-035 / CFR-GYM-006 / AFR-GYM-031."""
    club = _club()
    client = _client(stub_iam, 101, ("gymkhana.budget.view", "gymkhana.budget.create"))
    file = SimpleUploadedFile("budget.pdf", b"Budget", content_type="application/pdf")
    create_response = client.post(
        "/api/v1/gymkhana/budgets/",
        {
            "club_id": club.id,
            "amount": "100.00",
            "purpose": "Equipment",
            "supporting_file": file,
        },
        format="multipart",
    )
    assert create_response.status_code == 201
    budget_id = create_response.data["id"]
    detail_response = client.get(f"/api/v1/gymkhana/budgets/{budget_id}/")
    assert detail_response.status_code == 200
    assert detail_response.data["status"] == "open"
    assert client.patch(
        f"/api/v1/gymkhana/budgets/{budget_id}/",
        {"status": "approved"},
        format="json",
    ).status_code in (404, 405)
    assert client.put(
        f"/api/v1/gymkhana/budgets/{budget_id}/",
        {"status": "rejected"},
        format="json",
    ).status_code in (404, 405)


def test_FR_036_CFR_GYM_007_AFR_GYM_032_club_head_submits_event_report(
    stub_iam, gymkhana_users
):
    """FR-036 / CFR-GYM-007 / AFR-GYM-032."""
    club = _club()
    client = _client(stub_iam, 101, ("gymkhana.report.view", "gymkhana.report.create"))
    file = SimpleUploadedFile("report.pdf", b"Report", content_type="application/pdf")
    response = client.post(
        "/api/v1/gymkhana/reports/",
        {
            "club_id": club.id,
            "student_incharge_id": 103,
            "event_name": "Autumn Fest",
            "event_date": "2026-11-20T18:00:00Z",
            "description": "Fest report",
            "report_file": file,
        },
        format="multipart",
    )
    assert response.status_code == 201
    assert ClubEventReport.objects.filter(id=response.data["id"], club=club).exists()


def test_FR_037_CFR_GYM_007_AFR_GYM_033_missing_report_file_rejected(
    stub_iam, gymkhana_users
):
    """FR-037 / CFR-GYM-007 / AFR-GYM-033."""
    club = _club()
    client = _client(stub_iam, 101, ("gymkhana.report.view", "gymkhana.report.create"))
    count = ClubEventReport.objects.count()
    response = client.post(
        "/api/v1/gymkhana/reports/",
        {
            "club_id": club.id,
            "student_incharge_id": 103,
            "event_name": "Missing File",
            "event_date": "2026-11-20T18:00:00Z",
        },
        format="multipart",
    )
    assert response.status_code == 400
    assert ClubEventReport.objects.count() == count


def test_FR_038_CFR_GYM_007_AFR_GYM_034_assigned_faculty_accesses_reports(
    stub_iam, gymkhana_users
):
    """FR-038 / CFR-GYM-007 / AFR-GYM-034."""
    club = _club()
    ClubEventReport.objects.create(
        club=club,
        submitted_by_id=101,
        student_incharge_id=103,
        event_name="Club Event",
        event_date=datetime.datetime.now(datetime.UTC),
        description="Report",
    )
    client = _client(
        stub_iam,
        201,
        ("gymkhana.report.view",),
        kind="faculty",
        roles=("faculty",),
    )
    response = client.get(f"/api/v1/gymkhana/reports/?club_id={club.id}")
    assert response.status_code == 200
    assert response.data["results"]


def test_FR_039_CFR_GYM_007_AFR_GYM_034_unassigned_faculty_cannot_access_reports(
    stub_iam, gymkhana_users
):
    """FR-039 / CFR-GYM-007 / AFR-GYM-034."""
    club_x = _club(name="Club X")
    _club(name="Club Y", faculty_councillor_id=202)
    report = ClubEventReport.objects.create(
        club=club_x,
        submitted_by_id=101,
        student_incharge_id=103,
        event_name="Private Event",
        event_date=datetime.datetime.now(datetime.UTC),
        description="Private",
    )
    client = _client(
        stub_iam,
        202,
        ("gymkhana.report.view",),
        kind="faculty",
        roles=("faculty",),
    )
    list_response = client.get(f"/api/v1/gymkhana/reports/?club_id={club_x.id}")
    detail_response = client.get(f"/api/v1/gymkhana/reports/{report.id}/")
    assert list_response.status_code in (404, 200)
    if list_response.status_code == 200:
        assert report.id not in [item["id"] for item in list_response.data["results"]]
    assert detail_response.status_code == 404
