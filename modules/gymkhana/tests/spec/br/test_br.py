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
from modules.gymkhana.models.poll import Poll, PollChoice, PollTargetGroup, PollVote
from modules.gymkhana.models.report import ClubEventReport

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _temp_media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")


@pytest.fixture
def br_users():
    for uid, kind in ((101, "student"), (102, "student"), (103, "student"),
                      (104, "student"), (201, "faculty"), (202, "faculty"),
                      (301, "staff")):
        UserRef.objects.create(user_id=uid, username=f"br{uid}",
                               display_name=f"BR User {uid}", kind=kind, is_active=True)


def _client(stub_iam, uid, perms, kind="student", roles=("student",)):
    stub_iam(make_session(user_id=uid, kind=kind, roles=roles, modules=("gymkhana",),
                          permissions=perms))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token-123")
    return client


def _club(name="BR Club", status="confirmed", coordinator=101, cocoordinator=102,
          faculty=201):
    return Club.objects.create(name=name, category="technical", coordinator_id=coordinator,
                               co_coordinator_id=cocoordinator,
                               faculty_councillor_id=faculty, status=status)


def test_BR_001_BR_GYM_001_valid_student_coordinator(stub_iam, br_users):
    """BR-001 / BR-GYM-001 — valid student coordinator."""
    client = _client(stub_iam, 999, ("gymkhana.club.view", "gymkhana.club.create"),
                     roles=("student_admin",))
    count = Club.objects.count()
    response = client.post("/api/v1/gymkhana/clubs/", {"name": "BR001",
        "category": "technical", "coordinator_id": 301, "co_coordinator_id": 102,
        "faculty_councillor_id": 201}, format="json")
    assert response.status_code == 400
    assert Club.objects.count() == count


def test_BR_002_BR_GYM_001_valid_student_co_coordinator(stub_iam, br_users):
    """BR-002 / BR-GYM-001 — valid student co-coordinator."""
    client = _client(stub_iam, 999, ("gymkhana.club.view", "gymkhana.club.create"),
                     roles=("student_admin",))
    count = Club.objects.count()
    response = client.post("/api/v1/gymkhana/clubs/", {"name": "BR002",
        "category": "technical", "coordinator_id": 101, "co_coordinator_id": 301,
        "faculty_councillor_id": 201}, format="json")
    assert response.status_code == 400
    assert Club.objects.count() == count


def test_BR_003_BR_GYM_001_valid_replacement_leader(stub_iam, br_users):
    """BR-003 / BR-GYM-001 — valid replacement leader on leadership change."""
    club = _club("BR003")
    client = _client(stub_iam, 101, ("gymkhana.club.manage",))
    response = client.post(f"/api/v1/gymkhana/clubs/{club.id}/leadership/",
                           {"coordinator_id": 301, "co_coordinator_id": 104}, format="json")
    assert response.status_code == 400
    club.refresh_from_db()
    assert (club.coordinator_id, club.co_coordinator_id) == (101, 102)


def test_BR_004_BR_GYM_002_valid_faculty_councillor_creation(stub_iam, br_users):
    """BR-004 / BR-GYM-002 — valid faculty councillor on club creation."""
    client = _client(stub_iam, 999, ("gymkhana.club.view", "gymkhana.club.create"),
                     roles=("student_admin",))
    count = Club.objects.count()
    response = client.post("/api/v1/gymkhana/clubs/", {"name": "BR004",
        "category": "sports", "coordinator_id": 101, "co_coordinator_id": 102,
        "faculty_councillor_id": 103}, format="json")
    assert response.status_code == 400
    assert Club.objects.count() == count


def test_BR_005_BR_GYM_002_valid_faculty_councillor_event(stub_iam, br_users):
    """BR-005 / BR-GYM-002 — valid faculty councillor on event booking."""
    club = _club("BR005")
    client = _client(stub_iam, 101, ("gymkhana.booking.create",))
    count = VenueBooking.objects.count()
    response = client.post("/api/v1/gymkhana/bookings/event/", {
        "club_id": club.id, "name": "BR Event", "venue": "Hall 1",
        "booking_date": "2026-12-10", "start_time": "10:00:00", "end_time": "12:00:00",
        "faculty_councillor_id": 103,
    }, format="json")
    assert response.status_code == 400
    assert VenueBooking.objects.count() == count


def test_BR_006_BR_GYM_003_allowed_categories_accepted(stub_iam, br_users):
    """BR-006 / BR-GYM-003 — allowed categories accepted."""
    client = _client(stub_iam, 999, ("gymkhana.club.view", "gymkhana.club.create"),
                     roles=("student_admin",))
    for index, category in enumerate(("technical", "sports", "cultural"), 1):
        response = client.post("/api/v1/gymkhana/clubs/", {"name": f"BR006-{index}",
            "category": category, "coordinator_id": 101, "co_coordinator_id": 102,
            "faculty_councillor_id": 201}, format="json")
        assert response.status_code == 201
    assert Club.objects.filter(name__startswith="BR006-").count() == 3


def test_BR_007_BR_GYM_003_disallowed_category_rejected(stub_iam, br_users):
    """BR-007 / BR-GYM-003 — disallowed category rejected."""
    client = _client(stub_iam, 999, ("gymkhana.club.view", "gymkhana.club.create"),
                     roles=("student_admin",))
    count = Club.objects.count()
    response = client.post("/api/v1/gymkhana/clubs/", {"name": "BR007",
        "category": "arts", "coordinator_id": 101, "co_coordinator_id": 102,
        "faculty_councillor_id": 201}, format="json")
    assert response.status_code == 400
    assert Club.objects.count() == count


def test_BR_008_BR_GYM_004_new_club_starts_open(stub_iam, br_users):
    """BR-008 / BR-GYM-004 — new club starts as open."""
    client = _client(stub_iam, 999, ("gymkhana.club.view", "gymkhana.club.create"),
                     roles=("student_admin",))
    response = client.post("/api/v1/gymkhana/clubs/", {"name": "BR008",
        "category": "technical", "coordinator_id": 101, "co_coordinator_id": 102,
        "faculty_councillor_id": 201}, format="json")
    assert response.status_code == 201
    assert response.data["status"] == "open"
    assert Club.objects.get(id=response.data["id"]).status == "open"


def test_BR_009_BR_GYM_004_only_student_admin_confirm(stub_iam, br_users):
    """BR-009 / BR-GYM-004 — only Student Admin can confirm club."""
    club = _club("BR009", status="open")
    client = _client(stub_iam, 101, ("gymkhana.club.approve",))
    response = client.post(f"/api/v1/gymkhana/clubs/{club.id}/confirm/")
    assert response.status_code == 403
    club.refresh_from_db()
    assert club.status == "open"


def test_BR_010_BR_GYM_004_confirmation_changes_status(stub_iam, br_users):
    """BR-010 / BR-GYM-004 — confirmation changes status to confirmed."""
    club = _club("BR010", status="open")
    client = _client(stub_iam, 999, ("gymkhana.club.approve",), roles=("student_admin",))
    response = client.post(f"/api/v1/gymkhana/clubs/{club.id}/confirm/")
    assert response.status_code == 200
    club.refresh_from_db()
    assert club.status == "confirmed"


def test_BR_011_BR_GYM_005_start_before_end_accepted(stub_iam, br_users):
    """BR-011 / BR-GYM-005 — start before end accepted."""
    club = _club("BR011")
    client = _client(stub_iam, 101, ("gymkhana.booking.create",))
    response = client.post("/api/v1/gymkhana/bookings/session/", {
        "club_id": club.id, "venue": "Hall 1", "booking_date": "2026-12-10",
        "start_time": "10:00:00", "end_time": "11:00:00",
    }, format="json")
    assert response.status_code == 201


@pytest.mark.parametrize(
    ("start_time", "end_time"),
    (("10:00:00", "10:00:00"),),
)
def test_BR_012_BR_GYM_005_equal_start_end_rejected(stub_iam, br_users,
                                                     start_time, end_time):
    """BR-012 / BR-GYM-005 — equal start and end time rejected."""
    club = _club("BR012")
    client = _client(stub_iam, 101, ("gymkhana.booking.create",))
    count = VenueBooking.objects.count()
    response = client.post("/api/v1/gymkhana/bookings/session/", {
        "club_id": club.id, "venue": "Hall 1", "booking_date": "2026-12-10",
        "start_time": start_time, "end_time": end_time,
    }, format="json")
    assert response.status_code == 400
    assert VenueBooking.objects.count() == count


def test_BR_013_BR_GYM_005_end_before_start_rejected(stub_iam, br_users):
    """BR-013 / BR-GYM-005 — end before start rejected."""
    club = _club("BR013")
    client = _client(stub_iam, 101, ("gymkhana.booking.create",))
    count = VenueBooking.objects.count()
    response = client.post("/api/v1/gymkhana/bookings/session/", {
        "club_id": club.id, "venue": "Hall 1", "booking_date": "2026-12-10",
        "start_time": "12:00:00", "end_time": "10:00:00",
    }, format="json")
    assert response.status_code == 400
    assert VenueBooking.objects.count() == count


def test_BR_014_BR_GYM_006_session_session_overlap(stub_iam, br_users):
    """BR-014 / BR-GYM-006 — session-session overlap rejected."""
    club = _club("BR014")
    VenueBooking.objects.create(club=club, booking_type="session", venue="Hall 1",
        booking_date=datetime.date(2026, 12, 10), start_time=datetime.time(10),
        end_time=datetime.time(12), booked_by_id=101)
    client = _client(stub_iam, 101, ("gymkhana.booking.create",))
    count = VenueBooking.objects.count()
    response = client.post("/api/v1/gymkhana/bookings/session/", {
        "club_id": club.id, "venue": "Hall 1", "booking_date": "2026-12-10",
        "start_time": "11:00:00", "end_time": "13:00:00",
    }, format="json")
    assert response.status_code in (400, 409)
    assert VenueBooking.objects.count() == count


def test_BR_015_BR_GYM_006_event_event_overlap(stub_iam, br_users):
    """BR-015 / BR-GYM-006 — event-event overlap rejected."""
    club = _club("BR015")
    VenueBooking.objects.create(club=club, booking_type="event", venue="Hall 1",
        booking_date=datetime.date(2026, 12, 10), start_time=datetime.time(10),
        end_time=datetime.time(12), faculty_councillor_id=201, booked_by_id=101)
    client = _client(stub_iam, 101, ("gymkhana.booking.create",))
    count = VenueBooking.objects.count()
    response = client.post("/api/v1/gymkhana/bookings/event/", {
        "club_id": club.id, "name": "BR Event", "venue": "Hall 1",
        "booking_date": "2026-12-10", "start_time": "11:00:00", "end_time": "13:00:00",
        "faculty_councillor_id": 201,
    }, format="json")
    assert response.status_code in (400, 409)
    assert VenueBooking.objects.count() == count


def test_BR_016_BR_GYM_006_session_event_cross_overlap(stub_iam, br_users):
    """BR-016 / BR-GYM-006 — session-event cross-type overlap rejected."""
    club = _club("BR016")
    VenueBooking.objects.create(club=club, booking_type="event", venue="Hall 1",
        booking_date=datetime.date(2026, 12, 10), start_time=datetime.time(10),
        end_time=datetime.time(12), faculty_councillor_id=201, booked_by_id=101)
    client = _client(stub_iam, 101, ("gymkhana.booking.create",))
    count = VenueBooking.objects.count()
    response = client.post("/api/v1/gymkhana/bookings/session/", {
        "club_id": club.id, "venue": "Hall 1", "booking_date": "2026-12-10",
        "start_time": "11:00:00", "end_time": "13:00:00",
    }, format="json")
    assert response.status_code in (400, 409)
    assert VenueBooking.objects.count() == count


def test_BR_017_BR_GYM_006_event_session_cross_overlap(stub_iam, br_users):
    """BR-017 / BR-GYM-006 — event-session cross-type overlap rejected."""
    club = _club("BR017")
    VenueBooking.objects.create(club=club, booking_type="session", venue="Hall 1",
        booking_date=datetime.date(2026, 12, 10), start_time=datetime.time(10),
        end_time=datetime.time(12), booked_by_id=101)
    client = _client(stub_iam, 101, ("gymkhana.booking.create",))
    count = VenueBooking.objects.count()
    response = client.post("/api/v1/gymkhana/bookings/event/", {
        "club_id": club.id, "name": "BR Event", "venue": "Hall 1",
        "booking_date": "2026-12-10", "start_time": "11:00:00", "end_time": "13:00:00",
        "faculty_councillor_id": 201,
    }, format="json")
    assert response.status_code in (400, 409)
    assert VenueBooking.objects.count() == count


def test_BR_018_BR_GYM_006_non_overlapping_booking_accepted(stub_iam, br_users):
    """BR-018 / BR-GYM-006 — non-overlapping same-venue booking accepted."""
    club = _club("BR018")
    VenueBooking.objects.create(club=club, booking_type="session", venue="Hall 1",
        booking_date=datetime.date(2026, 12, 10), start_time=datetime.time(10),
        end_time=datetime.time(12), booked_by_id=101)
    client = _client(stub_iam, 101, ("gymkhana.booking.create",))
    response = client.post("/api/v1/gymkhana/bookings/session/", {
        "club_id": club.id, "venue": "Hall 1", "booking_date": "2026-12-10",
        "start_time": "12:00:00", "end_time": "14:00:00",
    }, format="json")
    assert response.status_code == 201


def test_BR_019_BR_GYM_007_membership_rejected_for_open_club(stub_iam, br_users):
    """BR-019 / BR-GYM-007 — membership only for confirmed club."""
    club = _club("BR019", status="open")
    client = _client(stub_iam, 103, ("gymkhana.membership.create",))
    count = ClubMembership.objects.count()
    response = client.post("/api/v1/gymkhana/memberships/apply/",
                           {"club_id": club.id}, format="json")
    assert response.status_code in (400, 409)
    assert ClubMembership.objects.count() == count


def test_BR_020_BR_GYM_007_membership_allowed_confirmed_club(stub_iam, br_users):
    """BR-020 / BR-GYM-007 — membership allowed for confirmed club."""
    club = _club("BR020")
    client = _client(stub_iam, 103, ("gymkhana.membership.create",))
    response = client.post("/api/v1/gymkhana/memberships/apply/",
                           {"club_id": club.id}, format="json")
    assert response.status_code == 201


def test_BR_021_BR_GYM_008_multiple_different_club_applications(stub_iam, br_users):
    """BR-021 / BR-GYM-008 — multiple different-club applications allowed."""
    club_a = _club("BR021A")
    club_b = _club("BR021B")
    client = _client(stub_iam, 103, ("gymkhana.membership.create",))
    first = client.post("/api/v1/gymkhana/memberships/apply/", {"club_id": club_a.id}, format="json")
    second = client.post("/api/v1/gymkhana/memberships/apply/", {"club_id": club_b.id}, format="json")
    assert first.status_code == 201
    assert second.status_code == 201


def test_BR_022_BR_GYM_009_duplicate_same_club_rejected(stub_iam, br_users):
    """BR-022 / BR-GYM-009 — duplicate same-club application rejected."""
    club = _club("BR022")
    membership = ClubMembership.objects.create(club=club, student_id=103,
                                               description="Original", status="open")
    client = _client(stub_iam, 103, ("gymkhana.membership.create",))
    response = client.post("/api/v1/gymkhana/memberships/apply/",
                           {"club_id": club.id, "description": "Duplicate"}, format="json")
    assert response.status_code in (400, 409)
    membership.refresh_from_db()
    assert membership.status == "open"
    assert membership.description == "Original"


def test_BR_023_BR_GYM_010_coordinator_authorized(stub_iam, br_users):
    """BR-023 / BR-GYM-010 — Club Head authorization accepted for coordinator."""
    club = _club("BR023")
    client = _client(stub_iam, 101, ("gymkhana.booking.create",))
    response = client.post("/api/v1/gymkhana/bookings/session/", {
        "club_id": club.id, "venue": "Hall 1", "booking_date": "2026-12-10",
        "start_time": "10:00:00", "end_time": "12:00:00",
    }, format="json")
    assert response.status_code == 201


def test_BR_024_BR_GYM_010_non_club_head_rejected(stub_iam, br_users):
    """BR-024 / BR-GYM-010 — non-Club-Head rejected."""
    club = _club("BR024")
    client = _client(stub_iam, 103, ("gymkhana.booking.create",))
    count = VenueBooking.objects.count()
    response = client.post("/api/v1/gymkhana/bookings/session/", {
        "club_id": club.id, "venue": "Hall 1", "booking_date": "2026-12-10",
        "start_time": "10:00:00", "end_time": "12:00:00",
    }, format="json")
    assert response.status_code == 403
    assert VenueBooking.objects.count() == count


def test_BR_025_BR_GYM_011_membership_confirmed(stub_iam, br_users):
    """BR-025 / BR-GYM-011 — membership approval transitions to confirmed."""
    club = _club("BR025")
    membership = ClubMembership.objects.create(club=club, student_id=103,
                                               status="open")
    client = _client(stub_iam, 101, ("gymkhana.membership.approve",))
    response = client.post(f"/api/v1/gymkhana/memberships/{membership.id}/approve/",
                           {}, format="json")
    assert response.status_code == 200
    membership.refresh_from_db()
    assert membership.status == "confirmed"


def test_BR_026_BR_GYM_011_optional_remarks_retained(stub_iam, br_users):
    """BR-026 / BR-GYM-011 — optional remarks retained."""
    club = _club("BR026")
    membership = ClubMembership.objects.create(club=club, student_id=103,
                                               status="open")
    client = _client(stub_iam, 101, ("gymkhana.membership.approve",))
    response = client.post(f"/api/v1/gymkhana/memberships/{membership.id}/approve/",
                           {"remarks": "Well qualified"}, format="json")
    assert response.status_code == 200
    membership.refresh_from_db()
    assert membership.remarks == "Well qualified"


def test_BR_027_BR_GYM_012_exactly_two_choices_accepted(stub_iam, br_users):
    """BR-027 / BR-GYM-012 — exactly two choices accepted."""
    club = _club("BR027")
    client = _client(stub_iam, 101, ("gymkhana.poll.view", "gymkhana.poll.create"))
    expires = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1)).isoformat()
    response = client.post("/api/v1/gymkhana/polls/", {
        "club_id": club.id, "title": "BR027", "expires_at": expires,
        "choices": ["A", "B"], "target_groups": [{"batch": "all", "branch": "all"}],
    }, format="json")
    assert response.status_code == 201


def test_BR_028_BR_GYM_012_one_choice_rejected(stub_iam, br_users):
    """BR-028 / BR-GYM-012 — poll with one choice rejected."""
    club = _club("BR028")
    client = _client(stub_iam, 101, ("gymkhana.poll.view", "gymkhana.poll.create"))
    count = Poll.objects.count()
    response = client.post("/api/v1/gymkhana/polls/", {
        "club_id": club.id, "title": "BR028",
        "expires_at": (datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1)).isoformat(),
        "choices": ["A"],
    }, format="json")
    assert response.status_code == 400
    assert Poll.objects.count() == count


def test_BR_030_BR_GYM_014_eligible_student_accesses_active_poll(stub_iam, br_users):
    """BR-030 / BR-GYM-014 — eligible student in target group can access active poll."""
    club = _club("BR030")
    poll = Poll.objects.create(club=club, created_by_id=101, title="BR030",
        expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1),
        status="active")
    PollChoice.objects.create(poll=poll, choice_text="A")
    PollTargetGroup.objects.create(poll=poll, batch="2024", branch="CSE")
    client = _client(stub_iam, 103, ("gymkhana.poll.view",))
    response = client.get(f"/api/v1/gymkhana/polls/{poll.id}/")
    assert response.status_code == 200
    assert response.data["choices"]


def test_BR_031_BR_GYM_014_ineligible_student_cannot_vote(stub_iam, br_users):
    """BR-031 / BR-GYM-014 — ineligible student wrong batch/branch cannot vote."""
    club = _club("BR031")
    poll = Poll.objects.create(club=club, created_by_id=101, title="BR031",
        expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1),
        status="active")
    choice = PollChoice.objects.create(poll=poll, choice_text="A")
    PollTargetGroup.objects.create(poll=poll, batch="2024", branch="CSE")
    client = _client(stub_iam, 103, ("gymkhana.poll.vote",))
    count = PollVote.objects.count()
    response = client.post(f"/api/v1/gymkhana/polls/{poll.id}/vote/",
                           {"choice_id": choice.id}, format="json")
    assert response.status_code in (400, 403)
    assert PollVote.objects.count() == count


def test_BR_032_BR_GYM_014_expired_poll_cannot_vote(stub_iam, br_users):
    """BR-032 / BR-GYM-014 — expired poll access denied."""
    club = _club("BR032")
    poll = Poll.objects.create(club=club, created_by_id=101, title="BR032",
        expires_at=datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1),
        status="active")
    choice = PollChoice.objects.create(poll=poll, choice_text="A")
    PollTargetGroup.objects.create(poll=poll, batch="all", branch="all")
    client = _client(stub_iam, 103, ("gymkhana.poll.vote",))
    response = client.post(f"/api/v1/gymkhana/polls/{poll.id}/vote/",
                           {"choice_id": choice.id}, format="json")
    assert response.status_code == 400
    assert not PollVote.objects.filter(poll=poll).exists()


def test_BR_033_BR_GYM_015_one_vote_per_student(stub_iam, br_users):
    """BR-033 / BR-GYM-015 — one vote per student per poll enforced."""
    club = _club("BR033")
    poll = Poll.objects.create(club=club, created_by_id=101, title="BR033",
        expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1),
        status="active")
    choice = PollChoice.objects.create(poll=poll, choice_text="A")
    PollVote.objects.create(poll=poll, student_id=103, choice=choice)
    client = _client(stub_iam, 103, ("gymkhana.poll.vote",))
    response = client.post(f"/api/v1/gymkhana/polls/{poll.id}/vote/",
                           {"choice_id": choice.id}, format="json")
    assert response.status_code in (400, 409)
    choice.refresh_from_db()
    assert choice.vote_count == 0


def test_BR_034_BR_GYM_015_tally_incremented_once(stub_iam, br_users):
    """BR-034 / BR-GYM-015 — tally incremented atomically on accepted vote."""
    club = _club("BR034")
    poll = Poll.objects.create(club=club, created_by_id=101, title="BR034",
        expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1),
        status="active")
    choice = PollChoice.objects.create(poll=poll, choice_text="A")
    other = PollChoice.objects.create(poll=poll, choice_text="B")
    PollTargetGroup.objects.create(poll=poll, batch="all", branch="all")
    client = _client(stub_iam, 103, ("gymkhana.poll.vote",))
    response = client.post(f"/api/v1/gymkhana/polls/{poll.id}/vote/",
                           {"choice_id": choice.id}, format="json")
    assert response.status_code in (200, 201)
    choice.refresh_from_db()
    other.refresh_from_db()
    assert choice.vote_count == 1
    assert other.vote_count == 0


def test_BR_035_BR_GYM_016_leadership_succession_replaces_assignments(stub_iam, br_users):
    """BR-035 / BR-GYM-016 — leadership succession replaces active assignments."""
    club = _club("BR035")
    client = _client(stub_iam, 101, ("gymkhana.club.manage",))
    response = client.post(f"/api/v1/gymkhana/clubs/{club.id}/leadership/",
                           {"coordinator_id": 103, "co_coordinator_id": 104}, format="json")
    assert response.status_code == 200
    club.refresh_from_db()
    assert club.coordinator_id == 103
    assert club.co_coordinator_id == 104


def test_BR_036_BR_GYM_017_zero_budget_amount_accepted(stub_iam, br_users):
    """BR-036 / BR-GYM-017 — non-negative amount accepted at zero boundary."""
    club = _club("BR036")
    client = _client(stub_iam, 101, ("gymkhana.budget.view", "gymkhana.budget.create"))
    file = SimpleUploadedFile("budget.pdf", b"Budget", content_type="application/pdf")
    response = client.post("/api/v1/gymkhana/budgets/", {
        "club_id": club.id, "amount": "0.00", "purpose": "Boundary",
        "supporting_file": file,
    }, format="multipart")
    assert response.status_code == 201


def test_BR_037_BR_GYM_017_negative_budget_amount_rejected(stub_iam, br_users):
    """BR-037 / BR-GYM-017 — negative amount rejected."""
    club = _club("BR037")
    client = _client(stub_iam, 101, ("gymkhana.budget.view", "gymkhana.budget.create"))
    file = SimpleUploadedFile("budget.pdf", b"Budget", content_type="application/pdf")
    count = ClubBudgetRequest.objects.count()
    response = client.post("/api/v1/gymkhana/budgets/", {
        "club_id": club.id, "amount": "-0.01", "purpose": "Invalid",
        "supporting_file": file,
    }, format="multipart")
    assert response.status_code == 400
    assert ClubBudgetRequest.objects.count() == count


def test_BR_038_BR_GYM_018_missing_supporting_file_rejected(stub_iam, br_users):
    """BR-038 / BR-GYM-018 — missing supporting file rejected."""
    club = _club("BR038")
    client = _client(stub_iam, 101, ("gymkhana.budget.view", "gymkhana.budget.create"))
    count = ClubBudgetRequest.objects.count()
    response = client.post("/api/v1/gymkhana/budgets/", {
        "club_id": club.id, "amount": "100.00", "purpose": "Missing",
    }, format="multipart")
    assert response.status_code == 400
    assert ClubBudgetRequest.objects.count() == count


def test_BR_039_BR_GYM_019_missing_report_file_rejected(stub_iam, br_users):
    """BR-039 / BR-GYM-019 — missing report file rejected."""
    club = _club("BR039")
    client = _client(stub_iam, 101, ("gymkhana.report.view", "gymkhana.report.create"))
    count = ClubEventReport.objects.count()
    response = client.post("/api/v1/gymkhana/reports/", {
        "club_id": club.id, "student_incharge_id": 103, "event_name": "BR039",
        "event_date": "2026-11-20T18:00:00Z",
    }, format="multipart")
    assert response.status_code == 400
    assert ClubEventReport.objects.count() == count


def test_BR_040_BR_GYM_019_report_with_file_accepted(stub_iam, br_users):
    """BR-040 / BR-GYM-019 — report with file accepted."""
    club = _club("BR040")
    client = _client(stub_iam, 101, ("gymkhana.report.view", "gymkhana.report.create"))
    file = SimpleUploadedFile("report.pdf", b"Report", content_type="application/pdf")
    response = client.post("/api/v1/gymkhana/reports/", {
        "club_id": club.id, "student_incharge_id": 103, "event_name": "BR040",
        "event_date": "2026-11-20T18:00:00Z", "report_file": file,
    }, format="multipart")
    assert response.status_code == 201


def test_BR_041_BR_GYM_020_configured_venue_accepted(stub_iam, br_users):
    """BR-041 / BR-GYM-020 — booking with configured venue accepted."""
    club = _club("BR041")
    client = _client(stub_iam, 101, ("gymkhana.booking.create",))
    response = client.post("/api/v1/gymkhana/bookings/session/", {
        "club_id": club.id, "venue": "Hall 1", "booking_date": "2026-12-10",
        "start_time": "10:00:00", "end_time": "12:00:00",
    }, format="json")
    assert response.status_code == 201


def test_BR_042_BR_GYM_020_unconfigured_venue_rejected(stub_iam, br_users):
    """BR-042 / BR-GYM-020 — booking with unconfigured venue rejected."""
    club = _club("BR042")
    client = _client(stub_iam, 101, ("gymkhana.booking.create",))
    count = VenueBooking.objects.count()
    response = client.post("/api/v1/gymkhana/bookings/session/", {
        "club_id": club.id, "venue": "RandomHall_XYZ", "booking_date": "2026-12-10",
        "start_time": "10:00:00", "end_time": "12:00:00",
    }, format="json")
    assert response.status_code == 400
    assert VenueBooking.objects.count() == count


def test_BR_043_BR_GYM_021_assigned_councillor_accesses_reports(stub_iam, br_users):
    """BR-043 / BR-GYM-021 — assigned councillor can access club reports."""
    club = _club("BR043")
    ClubEventReport.objects.create(club=club, submitted_by_id=101,
                                   student_incharge_id=103, event_name="BR043",
                                   event_date=datetime.datetime.now(datetime.UTC))
    client = _client(stub_iam, 201, ("gymkhana.report.view",),
                     kind="faculty", roles=("faculty",))
    response = client.get(f"/api/v1/gymkhana/reports/?club_id={club.id}")
    assert response.status_code == 200
    assert response.data["results"]


def test_BR_044_BR_GYM_021_unassigned_faculty_denied_reports(stub_iam, br_users):
    """BR-044 / BR-GYM-021 — unassigned faculty denied access to club reports."""
    club_x = _club("BR044X")
    _club("BR044Y", faculty=202)
    report = ClubEventReport.objects.create(club=club_x, submitted_by_id=101,
                                            student_incharge_id=103, event_name="BR044",
                                            event_date=datetime.datetime.now(datetime.UTC))
    client = _client(stub_iam, 202, ("gymkhana.report.view",),
                     kind="faculty", roles=("faculty",))
    response = client.get(f"/api/v1/gymkhana/reports/?club_id={club_x.id}")
    detail = client.get(f"/api/v1/gymkhana/reports/{report.id}/")
    assert response.status_code in (403, 404, 200)
    if response.status_code == 200:
        assert report.id not in [item["id"] for item in response.data["results"]]
    assert detail.status_code in (403, 404)
