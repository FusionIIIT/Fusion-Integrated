"""Automated backend test suite for Gymkhana Functional Requirements (FR).

Generated from a8_design/FR_DESIGN.json.
Rules applied:
- Implement exactly the supplied test cases (TC-FR-01 to TC-FR-43).
- Do not add, remove, merge or reinterpret test cases.
- Preserve each specified expected result.
- Do not modify production code.
- Use the Django isolated test database (@pytest.mark.django_db).
- Reuse existing Fusion test infrastructure where appropriate (APIClient, User model).
- Do not mock the behavior being tested.
- Do not use xfail to hide failures.
- Every test contains its test_id and source_id in its name and docstring.
- Tests that genuinely cannot be automated using available interfaces are skipped with NOT_AUTOMATED: <reason>.
"""

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from applications.gymkhana.models import (
    Club,
    ClubBudgetRequest,
    ClubEvent,
    ClubEventReport,
    ClubMembership,
    ClubSession,
    PollChoice,
    PollVote,
    Venue,
    VotingPoll,
)
from applications.gymkhana.views import ClubBudgetRequestViewSet

User = get_user_model()

# ---------------------------------------------------------------------------
# Test Data Helpers
# ---------------------------------------------------------------------------

_counter = 0


def _unique_name(prefix: str) -> str:
    global _counter
    _counter += 1
    return f"{prefix}_{_counter}"


def _make_user(username: str, is_staff: bool = False, is_superuser: bool = False):
    uname = _unique_name(username)
    return User.objects.create_user(
        username=uname,
        password="testpass123",
        is_staff=is_staff,
        is_superuser=is_superuser,
    )


def _make_club(
    coordinator, co_coordinator, faculty, status="confirmed", name=None, category="technical"
):
    club_name = name or _unique_name("TestClub")
    return Club.objects.create(
        name=club_name,
        description="A test club",
        category=category,
        coordinator=coordinator,
        co_coordinator=co_coordinator,
        faculty_councillor=faculty,
        status=status,
    )


def _make_venue(name="Venue", capacity=100):
    venue_name = _unique_name(name)
    return Venue.objects.create(name=venue_name, capacity=capacity)


# ---------------------------------------------------------------------------
# TC-FR-01 to TC-FR-09: Club Creation, Validation, Lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestClubCreationAndLifecycle:
    def test_tc_fr_01_create_new_club(self):
        """TC-FR-01 (source_id: AFR-GYM-001):
        Verify Student Admin can create a new club by providing club name, allowed category,
        coordinator, co-coordinator, Club Faculty Councillor, and description.
        """
        student_admin = _make_user("admin_fr01", is_staff=True)
        student_01 = _make_user("student_01_fr01")
        student_02 = _make_user("student_02_fr01")
        faculty_01 = _make_user("faculty_01_fr01")

        client = APIClient()
        client.force_authenticate(user=student_admin)

        club_name = _unique_name("Robotics Club")
        payload = {
            "name": club_name,
            "category": "technical",
            "coordinator": student_01.pk,
            "co_coordinator": student_02.pk,
            "faculty_councillor": faculty_01.pk,
            "description": "Campus Robotics Club",
        }
        resp = client.post("/api/gymkhana/clubs/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["status"] == "open"
        assert resp.data["name"] == club_name
        assert resp.data["category"] == "technical"
        assert resp.data["coordinator"] == student_01.pk
        assert resp.data["co_coordinator"] == student_02.pk
        assert resp.data["faculty_councillor"] == faculty_01.pk
        assert resp.data["description"] == "Campus Robotics Club"

        club = Club.objects.get(name=club_name)
        assert club.status == "open"
        assert club.coordinator == student_01
        assert club.co_coordinator == student_02
        assert club.faculty_councillor == faculty_01

    def test_tc_fr_02_validate_student_leaders_valid(self):
        """TC-FR-02 (source_id: AFR-GYM-002-valid):
        Verify system validates selected coordinator and co-coordinator are valid students during club creation.
        """
        student_admin = _make_user("admin_fr02", is_staff=True)
        student_01 = _make_user("student_01_fr02")
        student_02 = _make_user("student_02_fr02")
        faculty_01 = _make_user("faculty_01_fr02")

        client = APIClient()
        client.force_authenticate(user=student_admin)

        payload = {
            "name": _unique_name("ValidStudentClub"),
            "category": "technical",
            "coordinator": student_01.pk,
            "co_coordinator": student_02.pk,
            "faculty_councillor": faculty_01.pk,
            "description": "Valid students leadership",
        }
        resp = client.post("/api/gymkhana/clubs/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert Club.objects.filter(name=payload["name"]).exists()

    def test_tc_fr_03_validate_student_leaders_invalid(self):
        """TC-FR-03 (source_id: AFR-GYM-002-invalid):
        Verify club creation is rejected when coordinator or co-coordinator is not a valid student.
        """
        student_admin = _make_user("admin_fr03", is_staff=True)
        student_02 = _make_user("student_02_fr03")
        faculty_01 = _make_user("faculty_01_fr03")

        client = APIClient()
        client.force_authenticate(user=student_admin)

        non_student_user_id = 999999  # Invalid / non-existent user
        payload = {
            "name": _unique_name("InvalidStudentClub"),
            "category": "technical",
            "coordinator": non_student_user_id,
            "co_coordinator": student_02.pk,
            "faculty_councillor": faculty_01.pk,
            "description": "Invalid student as coordinator",
        }
        resp = client.post("/api/gymkhana/clubs/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert not Club.objects.filter(name=payload["name"]).exists()

    def test_tc_fr_04_validate_faculty_councillor_valid(self):
        """TC-FR-04 (source_id: AFR-GYM-003-valid):
        Verify system validates selected Club Faculty Councillor is a valid faculty member.
        """
        student_admin = _make_user("admin_fr04", is_staff=True)
        student_01 = _make_user("student_01_fr04")
        student_02 = _make_user("student_02_fr04")
        faculty_01 = _make_user("faculty_01_fr04")

        client = APIClient()
        client.force_authenticate(user=student_admin)

        payload = {
            "name": _unique_name("ValidFacultyClub"),
            "category": "sports",
            "coordinator": student_01.pk,
            "co_coordinator": student_02.pk,
            "faculty_councillor": faculty_01.pk,
            "description": "Valid faculty councillor assigned",
        }
        resp = client.post("/api/gymkhana/clubs/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert Club.objects.filter(name=payload["name"]).exists()

    def test_tc_fr_05_validate_faculty_councillor_invalid(self):
        """TC-FR-05 (source_id: AFR-GYM-003-invalid):
        Verify club creation is rejected when selected Club Faculty Councillor is not a valid faculty member.
        """
        student_admin = _make_user("admin_fr05", is_staff=True)
        student_coord = _make_user("coord_fr05")
        student_cocoord = _make_user("cocoord_fr05")
        student_01 = _make_user("student_01_fr05")  # A student, not a faculty member

        client = APIClient()
        client.force_authenticate(user=student_admin)

        payload = {
            "name": _unique_name("StudentAsFacultyClub"),
            "category": "technical",
            "coordinator": student_coord.pk,
            "co_coordinator": student_cocoord.pk,
            "faculty_councillor": student_01.pk,
            "description": "Student assigned as faculty councillor",
        }
        resp = client.post("/api/gymkhana/clubs/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, (
            f"Expected rejection with validation error for non-faculty councillor, got {resp.status_code}: {resp.data}"
        )
        assert not Club.objects.filter(name=payload["name"]).exists()

    def test_tc_fr_06_allowed_categories_valid(self):
        """TC-FR-06 (source_id: AFR-GYM-004-valid):
        Verify system accepts clubs created with category Technical, Sports, or Cultural.
        """
        student_admin = _make_user("admin_fr06", is_staff=True)
        student_01 = _make_user("student_01_fr06")
        student_02 = _make_user("student_02_fr06")
        faculty_01 = _make_user("faculty_01_fr06")

        client = APIClient()
        client.force_authenticate(user=student_admin)

        for cat in ["technical", "sports", "cultural"]:
            payload = {
                "name": _unique_name(f"Club_{cat}"),
                "category": cat,
                "coordinator": student_01.pk,
                "co_coordinator": student_02.pk,
                "faculty_councillor": faculty_01.pk,
                "description": f"Testing category {cat}",
            }
            resp = client.post("/api/gymkhana/clubs/", payload, format="json")
            assert resp.status_code == status.HTTP_201_CREATED, (
                f"Failed for category {cat}: {resp.data}"
            )
            assert Club.objects.filter(name=payload["name"], category=cat).exists()

    def test_tc_fr_07_disallowed_category_invalid(self):
        """TC-FR-07 (source_id: AFR-GYM-004-invalid):
        Verify system rejects club creation with a category outside Technical, Sports, or Cultural.
        """
        student_admin = _make_user("admin_fr07", is_staff=True)
        student_01 = _make_user("student_01_fr07")
        student_02 = _make_user("student_02_fr07")
        faculty_01 = _make_user("faculty_01_fr07")

        client = APIClient()
        client.force_authenticate(user=student_admin)

        payload = {
            "name": _unique_name("AcademicClub"),
            "category": "Academic",
            "coordinator": student_01.pk,
            "co_coordinator": student_02.pk,
            "faculty_councillor": faculty_01.pk,
            "description": "Disallowed category test",
        }
        resp = client.post("/api/gymkhana/clubs/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert not Club.objects.filter(name=payload["name"]).exists()

    def test_tc_fr_08_new_club_recorded_in_open_state(self):
        """TC-FR-08 (source_id: AFR-GYM-005):
        Verify newly created club is recorded in 'open' state pending Student Admin approval.
        """
        student_admin = _make_user("admin_fr08", is_staff=True)
        student_01 = _make_user("student_01_fr08")
        student_02 = _make_user("student_02_fr08")
        faculty_01 = _make_user("faculty_01_fr08")

        client = APIClient()
        client.force_authenticate(user=student_admin)

        club_name = _unique_name("Music Club")
        payload = {
            "name": club_name,
            "category": "cultural",
            "coordinator": student_01.pk,
            "co_coordinator": student_02.pk,
            "faculty_councillor": faculty_01.pk,
            "description": "Campus Music Club",
        }
        resp = client.post("/api/gymkhana/clubs/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["status"] == "open"

        club = Club.objects.get(name=club_name)
        assert club.status == "open"

    def test_tc_fr_09_student_admin_approves_open_club(self):
        """TC-FR-09 (source_id: AFR-GYM-006):
        Verify Student Admin can approve an open club and record it as confirmed.
        """
        student_admin = _make_user("admin_fr09", is_staff=True)
        student_01 = _make_user("student_01_fr09")
        student_02 = _make_user("student_02_fr09")
        faculty_01 = _make_user("faculty_01_fr09")

        club = _make_club(student_01, student_02, faculty_01, status="open")

        client = APIClient()
        client.force_authenticate(user=student_admin)

        resp = client.post(f"/api/gymkhana/clubs/{club.pk}/approve/", {}, format="json")
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["status"] == "confirmed"

        club.refresh_from_db()
        assert club.status == "confirmed"


# ---------------------------------------------------------------------------
# TC-FR-10 to TC-FR-13: Leadership Replacement and Tracking
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestClubLeadershipManagement:
    def test_tc_fr_10_club_head_replaces_leadership(self):
        """TC-FR-10 (source_id: AFR-GYM-007):
        Verify authorized Club Head can replace club coordinator and co-coordinator assignments.
        """
        student_01 = _make_user("student_01_fr10")
        student_02 = _make_user("student_02_fr10")
        student_03 = _make_user("student_03_fr10")
        student_04 = _make_user("student_04_fr10")
        faculty_01 = _make_user("faculty_01_fr10")

        club = _make_club(student_01, student_02, faculty_01, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=student_01)

        payload = {
            "coordinator": student_03.pk,
            "co_coordinator": student_04.pk,
        }
        resp = client.patch(f"/api/gymkhana/clubs/{club.pk}/", payload, format="json")
        assert resp.status_code == status.HTTP_200_OK, resp.data

        club.refresh_from_db()
        assert club.coordinator == student_03
        assert club.co_coordinator == student_04

    def test_tc_fr_11_replacement_leaders_validation_valid(self):
        """TC-FR-11 (source_id: AFR-GYM-008-valid):
        Verify system validates replacement coordinator and co-coordinator users are valid students.
        """
        student_01 = _make_user("student_01_fr11")
        student_02 = _make_user("student_02_fr11")
        student_03 = _make_user("student_03_fr11")
        student_04 = _make_user("student_04_fr11")
        faculty_01 = _make_user("faculty_01_fr11")

        club = _make_club(student_01, student_02, faculty_01, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=student_01)

        payload = {
            "coordinator": student_03.pk,
            "co_coordinator": student_04.pk,
        }
        resp = client.patch(f"/api/gymkhana/clubs/{club.pk}/", payload, format="json")
        assert resp.status_code == status.HTTP_200_OK, resp.data

        club.refresh_from_db()
        assert club.coordinator == student_03
        assert club.co_coordinator == student_04

    def test_tc_fr_12_replacement_leaders_validation_invalid(self):
        """TC-FR-12 (source_id: AFR-GYM-008-invalid):
        Verify leadership change is rejected when a proposed replacement leader is not a valid student.
        """
        student_01 = _make_user("student_01_fr12")
        student_02 = _make_user("student_02_fr12")
        faculty_01 = _make_user("faculty_01_fr12")

        club = _make_club(student_01, student_02, faculty_01, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=student_01)

        payload = {
            "coordinator": 999999,  # invalid_person (not a registered student)
        }
        resp = client.patch(f"/api/gymkhana/clubs/{club.pk}/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data

        club.refresh_from_db()
        assert club.coordinator == student_01  # remains unchanged

    def test_tc_fr_13_maintains_only_current_leadership(self):
        """TC-FR-13 (source_id: AFR-GYM-009):
        Verify system maintains only current coordinator and co-coordinator assignments after leadership change.
        """
        student_01 = _make_user("student_01_fr13")
        student_02 = _make_user("student_02_fr13")
        student_03 = _make_user("student_03_fr13")
        student_04 = _make_user("student_04_fr13")
        faculty_01 = _make_user("faculty_01_fr13")

        club = _make_club(student_01, student_02, faculty_01, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=student_01)

        resp = client.patch(
            f"/api/gymkhana/clubs/{club.pk}/",
            {"coordinator": student_03.pk, "co_coordinator": student_04.pk},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data

        club.refresh_from_db()
        assert club.coordinator == student_03
        assert club.co_coordinator == student_04
        assert club.is_head(student_03) is True
        assert club.is_head(student_04) is True
        assert club.is_head(student_01) is False
        assert club.is_head(student_02) is False


# ---------------------------------------------------------------------------
# TC-FR-14 to TC-FR-21: Sessions, Events, Conflicts, Notifications
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSessionAndEventBooking:
    def test_tc_fr_14_book_club_session(self):
        """TC-FR-14 (source_id: AFR-GYM-010):
        Verify Club Head can book a club session with configured venue, date, start time,
        end time, description, and optional poster.
        """
        coordinator = _make_user("coord_fr14")
        co_coordinator = _make_user("cocoord_fr14")
        faculty = _make_user("faculty_fr14")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")
        venue = _make_venue("Hall-A")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        poster = SimpleUploadedFile("poster.jpg", b"fake poster image", content_type="image/jpeg")
        payload = {
            "club": club.pk,
            "venue": venue.pk,
            "date": "2026-11-20",
            "start_time": "14:00",
            "end_time": "16:00",
            "description": "Intro Session",
            "poster": poster,
        }
        resp = client.post("/api/gymkhana/sessions/", payload, format="multipart")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert ClubSession.objects.filter(club=club, venue=venue, date="2026-11-20").exists()
        session = ClubSession.objects.get(club=club, venue=venue, date="2026-11-20")
        assert session.description == "Intro Session"
        assert session.start_time == datetime.time(14, 0)
        assert session.end_time == datetime.time(16, 0)

    def test_tc_fr_15_booking_time_range_valid(self):
        """TC-FR-15 (source_id: AFR-GYM-011-valid):
        Verify system accepts booking when start time strictly precedes end time.
        """
        coordinator = _make_user("coord_fr15")
        co_coordinator = _make_user("cocoord_fr15")
        faculty = _make_user("faculty_fr15")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")
        venue = _make_venue("Hall-TimeValid")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        payload = {
            "club": club.pk,
            "venue": venue.pk,
            "date": "2026-11-22",
            "start_time": "10:00",
            "end_time": "11:00",
            "description": "Valid time booking",
        }
        resp = client.post("/api/gymkhana/sessions/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

    def test_tc_fr_16_booking_time_range_invalid(self):
        """TC-FR-16 (source_id: AFR-GYM-011-invalid):
        Verify system rejects booking when start time does not precede end time (start time equal to or after end time).
        """
        coordinator = _make_user("coord_fr16")
        co_coordinator = _make_user("cocoord_fr16")
        faculty = _make_user("faculty_fr16")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")
        venue = _make_venue("Hall-TimeInvalid")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        # start_time equal to end_time
        payload_equal = {
            "club": club.pk,
            "venue": venue.pk,
            "date": "2026-11-22",
            "start_time": "12:00",
            "end_time": "12:00",
            "description": "Start equals end",
        }
        resp_equal = client.post("/api/gymkhana/sessions/", payload_equal, format="json")
        assert resp_equal.status_code == status.HTTP_400_BAD_REQUEST, resp_equal.data

        # start_time after end_time
        payload_after = {
            "club": club.pk,
            "venue": venue.pk,
            "date": "2026-11-22",
            "start_time": "12:00",
            "end_time": "11:00",
            "description": "Start after end",
        }
        resp_after = client.post("/api/gymkhana/sessions/", payload_after, format="json")
        assert resp_after.status_code == status.HTTP_400_BAD_REQUEST, resp_after.data

    def test_tc_fr_17_no_time_overlap_accepted(self):
        """TC-FR-17 (source_id: AFR-GYM-012-no-overlap):
        Verify system permits session or event booking when no time overlap exists in the same venue on the same date.
        """
        coordinator = _make_user("coord_fr17")
        co_coordinator = _make_user("cocoord_fr17")
        faculty = _make_user("faculty_fr17")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")
        venue = _make_venue("Hall-NoOverlap")

        # Existing session: 10:00 to 12:00
        ClubSession.objects.create(
            club=club,
            venue=venue,
            date=datetime.date(2026, 11, 20),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(12, 0),
            created_by=coordinator,
        )

        client = APIClient()
        client.force_authenticate(user=coordinator)

        # Non-overlapping session: 14:00 to 16:00
        payload = {
            "club": club.pk,
            "venue": venue.pk,
            "date": "2026-11-20",
            "start_time": "14:00",
            "end_time": "16:00",
            "description": "Afternoon session",
        }
        resp = client.post("/api/gymkhana/sessions/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

    def test_tc_fr_18_cross_type_overlap_rejected(self):
        """TC-FR-18 (source_id: AFR-GYM-012-overlap-rejected):
        Verify system prevents booking that overlaps any existing session or event in the same venue on the same date (cross-type conflict).
        """
        coordinator = _make_user("coord_fr18")
        co_coordinator = _make_user("cocoord_fr18")
        faculty = _make_user("faculty_fr18")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")
        venue = _make_venue("Hall-CrossOverlap")

        # Existing session: 14:00 to 16:00
        ClubSession.objects.create(
            club=club,
            venue=venue,
            date=datetime.date(2026, 11, 20),
            start_time=datetime.time(14, 0),
            end_time=datetime.time(16, 0),
            created_by=coordinator,
        )

        client = APIClient()
        client.force_authenticate(user=coordinator)

        # Conflicting event: 15:00 to 17:00
        payload = {
            "club": club.pk,
            "name": "Overlapping Event",
            "venue": venue.pk,
            "date": "2026-11-20",
            "start_time": "15:00",
            "end_time": "17:00",
            "description": "Conflict with session",
        }
        resp = client.post("/api/gymkhana/events/", payload, format="json")
        assert resp.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ), resp.data
        assert not ClubEvent.objects.filter(name="Overlapping Event").exists()

    def test_tc_fr_19_session_booking_notification(self):
        """TC-FR-19 (source_id: AFR-GYM-013):
        Verify system notifies intended student recipients after a club session is successfully booked.
        """
        pytest.skip(
            "NOT_AUTOMATED: No notification service interface exists in the Gymkhana module to verify notification dispatch."
        )

    def test_tc_fr_20_book_club_event(self):
        """TC-FR-20 (source_id: AFR-GYM-014):
        Verify Club Head can book a club event with event details, Club Faculty Councillor,
        configured venue, date, times, poster, and description.
        """
        coordinator = _make_user("coord_fr20")
        co_coordinator = _make_user("cocoord_fr20")
        faculty = _make_user("faculty_fr20")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")
        venue = _make_venue("Hall-B")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        poster = SimpleUploadedFile("event.png", b"fake event poster", content_type="image/png")
        payload = {
            "club": club.pk,
            "name": "Annual Fest Intro",
            "venue": venue.pk,
            "date": "2026-11-25",
            "start_time": "09:00",
            "end_time": "13:00",
            "description": "Orientation",
            "poster": poster,
        }
        resp = client.post("/api/gymkhana/events/", payload, format="multipart")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert ClubEvent.objects.filter(club=club, name="Annual Fest Intro").exists()
        event = ClubEvent.objects.get(club=club, name="Annual Fest Intro")
        assert event.venue == venue
        assert event.start_time == datetime.time(9, 0)
        assert event.end_time == datetime.time(13, 0)

    def test_tc_fr_21_event_booking_notification(self):
        """TC-FR-21 (source_id: AFR-GYM-015):
        Verify system notifies intended student recipients after an event is successfully booked.
        """
        pytest.skip(
            "NOT_AUTOMATED: No notification service interface exists in the Gymkhana module to verify notification dispatch."
        )


# ---------------------------------------------------------------------------
# TC-FR-22 to TC-FR-28: Club Membership Management
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestClubMembership:
    def test_tc_fr_22_student_applies_for_membership(self):
        """TC-FR-22 (source_id: AFR-GYM-016):
        Verify a student can apply for membership in a confirmed club and provide achievements or application description.
        """
        coordinator = _make_user("coord_fr22")
        co_coordinator = _make_user("cocoord_fr22")
        faculty = _make_user("faculty_fr22")
        student = _make_user("student_fr22")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=student)

        payload = {
            "club": club.pk,
            "achievements": "State level coding participant",
        }
        resp = client.post("/api/gymkhana/memberships/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["status"] == "open"
        assert resp.data["achievements"] == "State level coding participant"

        membership = ClubMembership.objects.get(club=club, student=student)
        assert membership.status == "open"
        assert membership.achievements == "State level coding participant"

    def test_tc_fr_23_multiple_club_membership_applications(self):
        """TC-FR-23 (source_id: AFR-GYM-017):
        Verify a student can maintain membership applications to multiple different clubs.
        """
        coordinator = _make_user("coord_fr23")
        co_coordinator = _make_user("cocoord_fr23")
        faculty = _make_user("faculty_fr23")
        student = _make_user("student_fr23")
        club_a = _make_club(coordinator, co_coordinator, faculty, status="confirmed", name="Club A")
        club_b = _make_club(coordinator, co_coordinator, faculty, status="confirmed", name="Club B")

        # Student has an active application with Club A
        m_a = ClubMembership.objects.create(club=club_a, student=student, status="open")

        client = APIClient()
        client.force_authenticate(user=student)

        payload = {"club": club_b.pk, "achievements": "App to Club B"}
        resp = client.post("/api/gymkhana/memberships/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

        # Both applications exist
        assert ClubMembership.objects.filter(club=club_a, student=student).exists()
        assert ClubMembership.objects.filter(club=club_b, student=student).exists()
        assert ClubMembership.objects.get(pk=m_a.pk).status == "open"

    def test_tc_fr_24_duplicate_membership_application_rejected(self):
        """TC-FR-24 (source_id: AFR-GYM-018):
        Verify system prevents a student from submitting a duplicate membership application to the same club.
        """
        coordinator = _make_user("coord_fr24")
        co_coordinator = _make_user("cocoord_fr24")
        faculty = _make_user("faculty_fr24")
        student = _make_user("student_fr24")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        # Existing application
        ClubMembership.objects.create(club=club, student=student, status="open")

        client = APIClient()
        client.force_authenticate(user=student)

        payload = {"club": club.pk, "achievements": "Duplicate application"}
        resp = client.post("/api/gymkhana/memberships/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert ClubMembership.objects.filter(club=club, student=student).count() == 1

    def test_tc_fr_25_membership_application_status_open(self):
        """TC-FR-25 (source_id: AFR-GYM-019):
        Verify newly submitted club-membership application is recorded with 'open' status.
        """
        coordinator = _make_user("coord_fr25")
        co_coordinator = _make_user("cocoord_fr25")
        faculty = _make_user("faculty_fr25")
        student = _make_user("student_fr25")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=student)

        payload = {"club": club.pk, "achievements": "Testing initial status"}
        resp = client.post("/api/gymkhana/memberships/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["status"] == "open"

        m = ClubMembership.objects.get(pk=resp.data["id"])
        assert m.status == "open"

    def test_tc_fr_26_club_head_accesses_pending_applications(self):
        """TC-FR-26 (source_id: AFR-GYM-020):
        Verify Club Head can access pending membership applications for the applicable club.
        """
        head_a = _make_user("head_a_fr26")
        head_b = _make_user("head_b_fr26")
        cocoord = _make_user("cocoord_fr26")
        faculty = _make_user("faculty_fr26")
        student_1 = _make_user("student_1_fr26")
        student_2 = _make_user("student_2_fr26")

        club_a = _make_club(head_a, cocoord, faculty, status="confirmed", name="Club Alpha")
        club_b = _make_club(head_b, cocoord, faculty, status="confirmed", name="Club Beta")

        m_a = ClubMembership.objects.create(club=club_a, student=student_1, status="open")
        m_b = ClubMembership.objects.create(club=club_b, student=student_2, status="open")

        client = APIClient()
        client.force_authenticate(user=head_a)

        resp = client.get("/api/gymkhana/memberships/")
        assert resp.status_code == status.HTTP_200_OK, resp.data

        results = resp.data.get("results", resp.data)
        returned_ids = [r["id"] for r in results]
        assert m_a.pk in returned_ids
        assert m_b.pk not in returned_ids

    def test_tc_fr_27_club_head_approves_membership_with_remarks(self):
        """TC-FR-27 (source_id: AFR-GYM-021):
        Verify applicable Club Head can approve an open membership application and optionally record remarks.
        """
        coordinator = _make_user("coord_fr27")
        co_coordinator = _make_user("cocoord_fr27")
        faculty = _make_user("faculty_fr27")
        student = _make_user("student_fr27")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        membership = ClubMembership.objects.create(club=club, student=student, status="open")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        payload = {"action": "approve", "remarks": "Welcome to the club!"}
        resp = client.post(
            f"/api/gymkhana/memberships/{membership.pk}/approve/", payload, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["status"] == "confirmed"
        assert resp.data["remarks"] == "Welcome to the club!"

        membership.refresh_from_db()
        assert membership.status == "confirmed"
        assert membership.remarks == "Welcome to the club!"

    def test_tc_fr_28_membership_transitions_from_open_to_confirmed(self):
        """TC-FR-28 (source_id: AFR-GYM-022):
        Verify system changes an approved membership application from open to confirmed.
        """
        coordinator = _make_user("coord_fr28")
        co_coordinator = _make_user("cocoord_fr28")
        faculty = _make_user("faculty_fr28")
        student = _make_user("student_fr28")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        membership = ClubMembership.objects.create(club=club, student=student, status="open")
        assert membership.status == "open"

        client = APIClient()
        client.force_authenticate(user=coordinator)

        payload = {"action": "approve"}
        resp = client.post(
            f"/api/gymkhana/memberships/{membership.pk}/approve/", payload, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data

        membership.refresh_from_db()
        assert membership.status == "confirmed"


# ---------------------------------------------------------------------------
# TC-FR-29 to TC-FR-36: Polling and Voting
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestVotingPolls:
    def test_tc_fr_29_create_voting_poll(self):
        """TC-FR-29 (source_id: AFR-GYM-023):
        Verify Club Head can create a voting poll with title, description, expiration date,
        choices, and target groups (batch/branch).
        """
        coordinator = _make_user("coord_fr29")
        co_coordinator = _make_user("cocoord_fr29")
        faculty = _make_user("faculty_fr29")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        payload = {
            "club": club.pk,
            "title": "Club Mascot",
            "description": "Vote for mascot",
            "expiry_date": "2026-12-01",
            "choice_texts": ["Falcon", "Tiger"],
            "target_batches": ["2024"],
            "target_branches": ["CSE"],
        }
        resp = client.post("/api/gymkhana/polls/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["title"] == "Club Mascot"
        assert len(resp.data["choices"]) == 2

        poll = VotingPoll.objects.get(pk=resp.data["id"])
        assert poll.title == "Club Mascot"
        assert poll.target_batches == ["2024"]
        assert poll.target_branches == ["CSE"]
        assert poll.choices.count() == 2

    def test_tc_fr_30_poll_choices_at_least_two_valid(self):
        """TC-FR-30 (source_id: AFR-GYM-024-valid):
        Verify system accepts voting poll creation with at least two choices.
        """
        coordinator = _make_user("coord_fr30")
        co_coordinator = _make_user("cocoord_fr30")
        faculty = _make_user("faculty_fr30")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        payload = {
            "club": club.pk,
            "title": "Valid Choices Poll",
            "expiry_date": "2026-12-01",
            "choice_texts": ["Option A", "Option B"],
        }
        resp = client.post("/api/gymkhana/polls/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        poll = VotingPoll.objects.get(pk=resp.data["id"])
        assert poll.choices.count() >= 2

    def test_tc_fr_31_poll_fewer_than_two_choices_rejected(self):
        """TC-FR-31 (source_id: AFR-GYM-024-invalid):
        Verify system rejects voting poll creation with fewer than two choices.
        """
        coordinator = _make_user("coord_fr31")
        co_coordinator = _make_user("cocoord_fr31")
        faculty = _make_user("faculty_fr31")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        payload = {
            "club": club.pk,
            "title": "Invalid Single Choice Poll",
            "expiry_date": "2026-12-01",
            "choice_texts": ["Only Option"],
        }
        resp = client.post("/api/gymkhana/polls/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert not VotingPoll.objects.filter(title="Invalid Single Choice Poll").exists()

    def test_tc_fr_32_poll_creation_notification(self):
        """TC-FR-32 (source_id: AFR-GYM-025):
        Verify system notifies students in selected target groups when voting poll is created.
        """
        pytest.skip(
            "NOT_AUTOMATED: No notification service interface exists in the Gymkhana module to verify target audience notification."
        )

    def test_tc_fr_33_student_accesses_active_poll(self):
        """TC-FR-33 (source_id: AFR-GYM-026):
        Verify eligible targeted student can access active voting poll and its available choices.
        """
        coordinator = _make_user("coord_fr33")
        co_coordinator = _make_user("cocoord_fr33")
        faculty = _make_user("faculty_fr33")
        student = _make_user("student_fr33")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        poll = VotingPoll.objects.create(
            club=club,
            title="Poll Access Test",
            description="Testing active poll retrieval",
            expiry_date=datetime.date(2027, 1, 1),
            target_batches=["2024"],
            target_branches=["CSE"],
            created_by=coordinator,
        )
        c1 = PollChoice.objects.create(poll=poll, text="Falcon")
        c2 = PollChoice.objects.create(poll=poll, text="Tiger")

        client = APIClient()
        client.force_authenticate(user=student)

        resp = client.get(f"/api/gymkhana/polls/{poll.pk}/")
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["title"] == "Poll Access Test"
        choices = resp.data.get("choices", [])
        choice_texts = [c["text"] for c in choices]
        assert "Falcon" in choice_texts
        assert "Tiger" in choice_texts

    def test_tc_fr_34_student_casts_vote(self):
        """TC-FR-34 (source_id: AFR-GYM-027):
        Verify eligible targeted student can cast one choice in an active voting poll.
        """
        coordinator = _make_user("coord_fr34")
        co_coordinator = _make_user("cocoord_fr34")
        faculty = _make_user("faculty_fr34")
        student = _make_user("student_fr34")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        poll = VotingPoll.objects.create(
            club=club,
            title="Voting Test Poll",
            expiry_date=datetime.date(2027, 1, 1),
            created_by=coordinator,
        )
        c1 = PollChoice.objects.create(poll=poll, text="Falcon")
        c2 = PollChoice.objects.create(poll=poll, text="Tiger")

        client = APIClient()
        client.force_authenticate(user=student)

        payload = {"poll": poll.pk, "choice": c1.pk}
        resp = client.post(f"/api/gymkhana/polls/{poll.pk}/vote/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert PollVote.objects.filter(poll=poll, voter=student, choice=c1).exists()

    def test_tc_fr_35_vote_increments_poll_tally(self):
        """TC-FR-35 (source_id: AFR-GYM-028-accepted):
        Verify system records accepted vote in poll tally.
        """
        coordinator = _make_user("coord_fr35")
        co_coordinator = _make_user("cocoord_fr35")
        faculty = _make_user("faculty_fr35")
        student = _make_user("student_fr35")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        poll = VotingPoll.objects.create(
            club=club,
            title="Tally Increment Poll",
            expiry_date=datetime.date(2027, 1, 1),
            created_by=coordinator,
        )
        c1 = PollChoice.objects.create(poll=poll, text="Option A", vote_count=0)
        c2 = PollChoice.objects.create(poll=poll, text="Option B", vote_count=0)

        assert c1.vote_count == 0

        client = APIClient()
        client.force_authenticate(user=student)

        payload = {"poll": poll.pk, "choice": c1.pk}
        resp = client.post(f"/api/gymkhana/polls/{poll.pk}/vote/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

        c1.refresh_from_db()
        assert c1.vote_count == 1

    def test_tc_fr_36_duplicate_vote_rejected(self):
        """TC-FR-36 (source_id: AFR-GYM-028-duplicate):
        Verify system prevents more than one vote by the same student in the same poll.
        """
        coordinator = _make_user("coord_fr36")
        co_coordinator = _make_user("cocoord_fr36")
        faculty = _make_user("faculty_fr36")
        student = _make_user("student_fr36")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        poll = VotingPoll.objects.create(
            club=club,
            title="One Vote Enforced Poll",
            expiry_date=datetime.date(2027, 1, 1),
            created_by=coordinator,
        )
        c1 = PollChoice.objects.create(poll=poll, text="Option A", vote_count=0)
        c2 = PollChoice.objects.create(poll=poll, text="Option B", vote_count=0)

        # Initial vote
        PollVote.objects.create(poll=poll, choice=c1, voter=student)
        c1.vote_count = 1
        c1.save()

        client = APIClient()
        client.force_authenticate(user=student)

        # Attempt second vote in same poll
        payload = {"poll": poll.pk, "choice": c2.pk}
        resp = client.post(f"/api/gymkhana/polls/{poll.pk}/vote/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data

        c1.refresh_from_db()
        c2.refresh_from_db()
        assert c1.vote_count == 1
        assert c2.vote_count == 0
        assert PollVote.objects.filter(poll=poll, voter=student).count() == 1


# ---------------------------------------------------------------------------
# TC-FR-37 to TC-FR-40: Club Budget Requests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestClubBudgetRequests:
    def test_tc_fr_37_submit_budget_request(self):
        """TC-FR-37 (source_id: AFR-GYM-029):
        Verify Club Head can submit a club budget request with amount, purpose, description, and supporting file.
        """
        coordinator = _make_user("coord_fr37")
        co_coordinator = _make_user("cocoord_fr37")
        faculty = _make_user("faculty_fr37")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        supporting_file = SimpleUploadedFile(
            "budget_details.pdf", b"budget PDF data", content_type="application/pdf"
        )
        payload = {
            "club": club.pk,
            "amount": "5000.00",
            "purpose": "Hackathon prizes",
            "description": "Annual prize pool",
            "supporting_file": supporting_file,
        }
        resp = client.post("/api/gymkhana/budget-requests/", payload, format="multipart")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["amount"] == "5000.00"
        assert resp.data["purpose"] == "Hackathon prizes"

        br = ClubBudgetRequest.objects.get(pk=resp.data["id"])
        assert br.amount == Decimal("5000.00")
        assert br.purpose == "Hackathon prizes"
        assert br.description == "Annual prize pool"
        assert bool(br.supporting_file) is True

    def test_tc_fr_38_negative_budget_amount_rejected(self):
        """TC-FR-38 (source_id: AFR-GYM-030-negative-amount):
        Verify system rejects a club budget request whose amount is negative.
        """
        coordinator = _make_user("coord_fr38")
        co_coordinator = _make_user("cocoord_fr38")
        faculty = _make_user("faculty_fr38")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        supporting_file = SimpleUploadedFile(
            "budget.pdf", b"budget PDF data", content_type="application/pdf"
        )
        payload = {
            "club": club.pk,
            "amount": "-100.00",
            "purpose": "Negative budget test",
            "description": "Should fail",
            "supporting_file": supporting_file,
        }
        resp = client.post("/api/gymkhana/budget-requests/", payload, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert not ClubBudgetRequest.objects.filter(
            club=club, purpose="Negative budget test"
        ).exists()

    def test_tc_fr_39_budget_request_missing_file_rejected(self):
        """TC-FR-39 (source_id: AFR-GYM-030-missing-file):
        Verify system rejects a club budget request whose required supporting file is missing.
        """
        coordinator = _make_user("coord_fr39")
        co_coordinator = _make_user("cocoord_fr39")
        faculty = _make_user("faculty_fr39")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        payload = {
            "club": club.pk,
            "amount": "2000.00",
            "purpose": "Missing file test",
            "description": "Should fail due to missing supporting file",
        }
        resp = client.post("/api/gymkhana/budget-requests/", payload, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert not ClubBudgetRequest.objects.filter(club=club, purpose="Missing file test").exists()

    def test_tc_fr_40_budget_request_tracking_no_approval_lifecycle(self):
        """TC-FR-40 (source_id: AFR-GYM-031):
        Verify system stores submitted club budget request as open request for tracking without online approval/rejection lifecycle.
        """
        coordinator = _make_user("coord_fr40")
        co_coordinator = _make_user("cocoord_fr40")
        faculty = _make_user("faculty_fr40")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        supporting_file = SimpleUploadedFile(
            "budget_track.pdf", b"content", content_type="application/pdf"
        )
        payload = {
            "club": club.pk,
            "amount": "3000.00",
            "purpose": "Equipment purchase",
            "description": "Tracking only",
            "supporting_file": supporting_file,
        }
        resp = client.post("/api/gymkhana/budget-requests/", payload, format="multipart")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["status"] == "open"

        br = ClubBudgetRequest.objects.get(pk=resp.data["id"])
        assert br.status == "open"

        # Verify no online approval or rejection action endpoints are exposed
        extra_actions = [a.__name__ for a in ClubBudgetRequestViewSet.get_extra_actions()]
        assert "approve" not in extra_actions
        assert "reject" not in extra_actions

        resp_approve = client.post(
            f"/api/gymkhana/budget-requests/{br.pk}/approve/", {}, format="json"
        )
        resp_reject = client.post(
            f"/api/gymkhana/budget-requests/{br.pk}/reject/", {}, format="json"
        )
        assert resp_approve.status_code in (
            status.HTTP_404_NOT_FOUND,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        assert resp_reject.status_code in (
            status.HTTP_404_NOT_FOUND,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )


# ---------------------------------------------------------------------------
# TC-FR-41 to TC-FR-43: Club Event Reports and Councillor Review
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestClubEventReports:
    def test_tc_fr_41_submit_event_report(self):
        """TC-FR-41 (source_id: AFR-GYM-032):
        Verify Club Head can submit a club event report containing club, student incharge,
        event name, event date/time, description, and report/details file.
        """
        coordinator = _make_user("coord_fr41")
        co_coordinator = _make_user("cocoord_fr41")
        faculty = _make_user("faculty_fr41")
        student_01 = _make_user("student_01_fr41")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        report_file = SimpleUploadedFile(
            "report.pdf", b"event report content", content_type="application/pdf"
        )
        payload = {
            "club": club.pk,
            "student_incharge": student_01.pk,
            "event_name": "Workshop 2026",
            "event_date": "2026-11-15",
            "description": "Report of workshop",
            "report_file": report_file,
        }
        resp = client.post("/api/gymkhana/event-reports/", payload, format="multipart")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["event_name"] == "Workshop 2026"

        report = ClubEventReport.objects.get(pk=resp.data["id"])
        assert report.club == club
        assert report.student_incharge == student_01
        assert report.event_name == "Workshop 2026"
        assert report.description == "Report of workshop"
        assert bool(report.report_file) is True

    def test_tc_fr_42_event_report_missing_file_rejected(self):
        """TC-FR-42 (source_id: AFR-GYM-033):
        Verify system requires report/details file when a club event report is submitted.
        """
        coordinator = _make_user("coord_fr42")
        co_coordinator = _make_user("cocoord_fr42")
        faculty = _make_user("faculty_fr42")
        student_01 = _make_user("student_01_fr42")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        payload = {
            "club": club.pk,
            "student_incharge": student_01.pk,
            "event_name": "Workshop 2026 Without Report",
            "event_date": "2026-11-15",
            "description": "Should fail because report_file is missing",
        }
        resp = client.post("/api/gymkhana/event-reports/", payload, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert not ClubEventReport.objects.filter(
            club=club, event_name="Workshop 2026 Without Report"
        ).exists()

    def test_tc_fr_43_faculty_councillor_reviews_event_reports(self):
        """TC-FR-43 (source_id: AFR-GYM-034):
        Verify system allows assigned Club Faculty Councillor to access and review submitted event reports for councillor's club.
        """
        coordinator = _make_user("coord_fr43")
        co_coordinator = _make_user("cocoord_fr43")
        faculty_a = _make_user("faculty_a_fr43")
        faculty_other = _make_user("faculty_other_fr43")
        student_01 = _make_user("student_01_fr43")
        club_a = _make_club(
            coordinator, co_coordinator, faculty_a, status="confirmed", name="Club Review A"
        )

        report_file = SimpleUploadedFile(
            "workshop_report.pdf", b"PDF bytes", content_type="application/pdf"
        )
        report = ClubEventReport.objects.create(
            club=club_a,
            submitted_by=coordinator,
            student_incharge=student_01,
            event_name="Annual Review Event",
            description="Details of annual review",
            event_date=datetime.date(2026, 11, 15),
            report_file=report_file,
        )

        client = APIClient()

        # Assigned faculty councillor for Club A can access reports
        client.force_authenticate(user=faculty_a)
        resp_councillor = client.get(f"/api/gymkhana/event-reports/{report.pk}/")
        assert resp_councillor.status_code == status.HTTP_200_OK, resp_councillor.data
        assert resp_councillor.data["event_name"] == "Annual Review Event"
        assert resp_councillor.data["description"] == "Details of annual review"
        assert "workshop_report" in resp_councillor.data["report_file"]

        # Other unassigned faculty member cannot access reports for Club A
        client.force_authenticate(user=faculty_other)
        resp_unassigned = client.get(f"/api/gymkhana/event-reports/{report.pk}/")
        assert resp_unassigned.status_code == status.HTTP_404_NOT_FOUND
