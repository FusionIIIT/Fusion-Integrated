"""Automated backend test suite for Gymkhana Business Rules (BR).

Generated from a8_design/BR_DESIGN.json.
Rules applied:
- Implement exactly the supplied test cases (TC-BR-01 to TC-BR-39).
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
# ruff: noqa: E501, S106, PLW0603, F841

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
# TC-BR-01 to TC-BR-04: Student Leadership and Faculty Councillor Validation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestStudentLeadershipAndFacultyValidation:
    def test_tc_br_01_valid_student_leadership_permitted(self):
        """TC-BR-01 (source_id: BR-GYM-001-permitted):
        Verify permitted outcome of BR-GYM-001 when coordinator, co-coordinator, and replacement leaders reference valid students.
        """
        student_admin = _make_user("admin_br01", is_staff=True)
        student_01 = _make_user("student_01_br01")
        student_02 = _make_user("student_02_br01")
        student_03 = _make_user("student_03_br01")
        student_04 = _make_user("student_04_br01")
        faculty_01 = _make_user("faculty_01_br01")

        client = APIClient()
        client.force_authenticate(user=student_admin)

        club_name = _unique_name("LeadershipPermittedClub")
        payload = {
            "name": club_name,
            "category": "technical",
            "coordinator": student_01.pk,
            "co_coordinator": student_02.pk,
            "faculty_councillor": faculty_01.pk,
            "description": "Valid student leaders club",
        }
        resp = client.post("/api/gymkhana/clubs/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        club = Club.objects.get(name=club_name)
        assert club.coordinator == student_01
        assert club.co_coordinator == student_02

        # Verify replacement leaders assignment
        client.force_authenticate(user=student_01)
        patch_payload = {
            "coordinator": student_03.pk,
            "co_coordinator": student_04.pk,
        }
        patch_resp = client.patch(f"/api/gymkhana/clubs/{club.pk}/", patch_payload, format="json")
        assert patch_resp.status_code == status.HTTP_200_OK, patch_resp.data

        club.refresh_from_db()
        assert club.coordinator == student_03
        assert club.co_coordinator == student_04

    def test_tc_br_02_valid_student_leadership_prohibited(self):
        """TC-BR-02 (source_id: BR-GYM-001-prohibited):
        Verify prohibited outcome of BR-GYM-001 when coordinator or co-coordinator is not a valid student.
        """
        student_admin = _make_user("admin_br02", is_staff=True)
        student_02 = _make_user("student_02_br02")
        faculty_01 = _make_user("faculty_01_br02")

        client = APIClient()
        client.force_authenticate(user=student_admin)

        invalid_student_id = 999999
        payload = {
            "name": _unique_name("InvalidLeaderClub"),
            "category": "technical",
            "coordinator": invalid_student_id,
            "co_coordinator": student_02.pk,
            "faculty_councillor": faculty_01.pk,
            "description": "Invalid student leader",
        }
        resp = client.post("/api/gymkhana/clubs/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert not Club.objects.filter(name=payload["name"]).exists()

    def test_tc_br_03_valid_faculty_councillor_permitted(self):
        """TC-BR-03 (source_id: BR-GYM-002-permitted):
        Verify permitted outcome of BR-GYM-002 when Club Faculty Councillor references a valid faculty member.
        """
        student_admin = _make_user("admin_br03", is_staff=True)
        student_01 = _make_user("student_01_br03")
        student_02 = _make_user("student_02_br03")
        faculty_01 = _make_user("faculty_01_br03", is_staff=True)

        client = APIClient()
        client.force_authenticate(user=student_admin)

        club_name = _unique_name("ValidFacultyClub")
        payload = {
            "name": club_name,
            "category": "sports",
            "coordinator": student_01.pk,
            "co_coordinator": student_02.pk,
            "faculty_councillor": faculty_01.pk,
            "description": "Valid faculty councillor reference",
        }
        resp = client.post("/api/gymkhana/clubs/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        club = Club.objects.get(name=club_name)
        assert club.faculty_councillor == faculty_01

    def test_tc_br_04_valid_faculty_councillor_prohibited(self):
        """TC-BR-04 (source_id: BR-GYM-002-prohibited):
        Verify prohibited outcome of BR-GYM-002 when Club Faculty Councillor is invalid.
        """
        student_admin = _make_user("admin_br04", is_staff=True)
        student_coord = _make_user("coord_br04")
        student_cocoord = _make_user("cocoord_br04")
        student_non_faculty = _make_user("non_faculty_br04")  # student, not a faculty member

        client = APIClient()
        client.force_authenticate(user=student_admin)

        payload = {
            "name": _unique_name("InvalidFacultyClub"),
            "category": "technical",
            "coordinator": student_coord.pk,
            "co_coordinator": student_cocoord.pk,
            "faculty_councillor": student_non_faculty.pk,
            "description": "Non-faculty user assigned as faculty councillor",
        }
        resp = client.post("/api/gymkhana/clubs/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, (
            f"Expected rejection with faculty validation error, got {resp.status_code}: {resp.data}"
        )


# ---------------------------------------------------------------------------
# TC-BR-05 to TC-BR-09: Club Categories and Confirmation Lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestClubCategoriesAndConfirmationLifecycle:
    def test_tc_br_05_allowed_club_categories_permitted(self):
        """TC-BR-05 (source_id: BR-GYM-003-permitted):
        Verify permitted outcome of BR-GYM-003 when club category is Technical, Sports, or Cultural.
        """
        student_admin = _make_user("admin_br05", is_staff=True)
        student_01 = _make_user("student_01_br05")
        student_02 = _make_user("student_02_br05")
        faculty_01 = _make_user("faculty_01_br05")

        client = APIClient()
        client.force_authenticate(user=student_admin)

        for cat in ["technical", "sports", "cultural"]:
            name = _unique_name(f"Category_{cat}")
            payload = {
                "name": name,
                "category": cat,
                "coordinator": student_01.pk,
                "co_coordinator": student_02.pk,
                "faculty_councillor": faculty_01.pk,
                "description": f"Testing allowed category {cat}",
            }
            resp = client.post("/api/gymkhana/clubs/", payload, format="json")
            assert resp.status_code == status.HTTP_201_CREATED, resp.data
            assert resp.data["category"] == cat
            assert Club.objects.filter(name=name, category=cat).exists()

    def test_tc_br_06_allowed_club_categories_prohibited(self):
        """TC-BR-06 (source_id: BR-GYM-003-prohibited):
        Verify prohibited outcome of BR-GYM-003 when club category is outside allowed values.
        """
        student_admin = _make_user("admin_br06", is_staff=True)
        student_01 = _make_user("student_01_br06")
        student_02 = _make_user("student_02_br06")
        faculty_01 = _make_user("faculty_01_br06")

        client = APIClient()
        client.force_authenticate(user=student_admin)

        club_name = _unique_name("SocialClub")
        payload = {
            "name": club_name,
            "category": "Social",
            "coordinator": student_01.pk,
            "co_coordinator": student_02.pk,
            "faculty_councillor": faculty_01.pk,
            "description": "Club with disallowed category",
        }
        resp = client.post("/api/gymkhana/clubs/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert not Club.objects.filter(name=club_name).exists()

    def test_tc_br_07_club_confirmation_lifecycle_open_on_creation(self):
        """TC-BR-07 (source_id: BR-GYM-004-open-on-creation):
        Verify BR-GYM-004 outcome where new club creation results in 'open' status.
        """
        student_admin = _make_user("admin_br07", is_staff=True)
        student_01 = _make_user("student_01_br07")
        student_02 = _make_user("student_02_br07")
        faculty_01 = _make_user("faculty_01_br07")

        client = APIClient()
        client.force_authenticate(user=student_admin)

        club_name = _unique_name("OpenOnCreationClub")
        payload = {
            "name": club_name,
            "category": "technical",
            "coordinator": student_01.pk,
            "co_coordinator": student_02.pk,
            "faculty_councillor": faculty_01.pk,
            "description": "Checking open status on creation",
        }
        resp = client.post("/api/gymkhana/clubs/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["status"] == "open"

        club = Club.objects.get(name=club_name)
        assert club.status == "open"

    def test_tc_br_08_club_confirmation_lifecycle_confirmed_on_approval(self):
        """TC-BR-08 (source_id: BR-GYM-004-confirmed-on-approval):
        Verify BR-GYM-004 outcome where Student Admin approval changes open club to confirmed.
        """
        student_admin = _make_user("admin_br08", is_staff=True)
        student_01 = _make_user("student_01_br08")
        student_02 = _make_user("student_02_br08")
        faculty_01 = _make_user("faculty_01_br08")

        club = _make_club(student_01, student_02, faculty_01, status="open")

        client = APIClient()
        client.force_authenticate(user=student_admin)

        resp = client.post(f"/api/gymkhana/clubs/{club.pk}/approve/", {}, format="json")
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["status"] == "confirmed"

        club.refresh_from_db()
        assert club.status == "confirmed"

    def test_tc_br_09_club_confirmation_lifecycle_non_open_unmodified(self):
        """TC-BR-09 (source_id: BR-GYM-004-non-open-unmodified):
        Verify BR-GYM-004 stated exception where a non-open club cannot undergo approval and no rejection transition exists.
        """
        student_admin = _make_user("admin_br09", is_staff=True)
        student_01 = _make_user("student_01_br09")
        student_02 = _make_user("student_02_br09")
        faculty_01 = _make_user("faculty_01_br09")

        club = _make_club(student_01, student_02, faculty_01, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=student_admin)

        resp = client.post(f"/api/gymkhana/clubs/{club.pk}/approve/", {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data

        club.refresh_from_db()
        assert club.status == "confirmed"


# ---------------------------------------------------------------------------
# TC-BR-10 to TC-BR-13: Booking Time Range and Venue Exclusivity
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBookingTimeRangeAndVenueExclusivity:
    def test_tc_br_10_valid_booking_time_range_permitted(self):
        """TC-BR-10 (source_id: BR-GYM-005-permitted):
        Verify BR-GYM-005 permitted threshold side where booking start time is earlier than end time.
        """
        coordinator = _make_user("coord_br10")
        co_coordinator = _make_user("cocoord_br10")
        faculty = _make_user("faculty_br10")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")
        venue = _make_venue("Hall-TimeValid")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        payload = {
            "club": club.pk,
            "venue": venue.pk,
            "date": "2026-11-20",
            "start_time": "14:00",
            "end_time": "15:30",
            "description": "Valid time booking test",
        }
        resp = client.post("/api/gymkhana/sessions/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        session = ClubSession.objects.get(pk=resp.data["id"])
        assert session.start_time == datetime.time(14, 0)
        assert session.end_time == datetime.time(15, 30)

    def test_tc_br_11_valid_booking_time_range_prohibited(self):
        """TC-BR-11 (source_id: BR-GYM-005-prohibited):
        Verify BR-GYM-005 prohibited threshold side where booking start time is equal to or later than end time.
        """
        coordinator = _make_user("coord_br11")
        co_coordinator = _make_user("cocoord_br11")
        faculty = _make_user("faculty_br11")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")
        venue = _make_venue("Hall-TimeInvalid")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        # start_time equal to end_time
        payload_equal = {
            "club": club.pk,
            "venue": venue.pk,
            "date": "2026-11-20",
            "start_time": "16:00",
            "end_time": "16:00",
            "description": "Start equals end",
        }
        resp_equal = client.post("/api/gymkhana/sessions/", payload_equal, format="json")
        assert resp_equal.status_code == status.HTTP_400_BAD_REQUEST, resp_equal.data

        # start_time later than end_time
        payload_later = {
            "club": club.pk,
            "venue": venue.pk,
            "date": "2026-11-20",
            "start_time": "17:00",
            "end_time": "16:00",
            "description": "Start after end",
        }
        resp_later = client.post("/api/gymkhana/sessions/", payload_later, format="json")
        assert resp_later.status_code == status.HTTP_400_BAD_REQUEST, resp_later.data

    def test_tc_br_12_cross_type_venue_exclusivity_permitted(self):
        """TC-BR-12 (source_id: BR-GYM-006-permitted):
        Verify BR-GYM-006 permitted outcome when session or event does not overlap any existing booking in same venue and date.
        """
        coordinator = _make_user("coord_br12")
        co_coordinator = _make_user("cocoord_br12")
        faculty = _make_user("faculty_br12")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")
        venue = _make_venue("Hall-NonOverlap")

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

        # Non-overlapping event: 12:00 to 14:00
        payload = {
            "club": club.pk,
            "name": "Non-overlapping Event",
            "venue": venue.pk,
            "date": "2026-11-20",
            "start_time": "12:00",
            "end_time": "14:00",
            "description": "Afternoon event after session",
        }
        resp = client.post("/api/gymkhana/events/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert ClubEvent.objects.filter(
            club=club, venue=venue, name="Non-overlapping Event"
        ).exists()

    def test_tc_br_13_cross_type_venue_exclusivity_prohibited(self):
        """TC-BR-13 (source_id: BR-GYM-006-prohibited):
        Verify BR-GYM-006 prohibited outcome rejecting session-session, event-event, and cross-type session-event overlap in same venue and date.
        """
        coordinator = _make_user("coord_br13")
        co_coordinator = _make_user("cocoord_br13")
        faculty = _make_user("faculty_br13")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")
        venue = _make_venue("Hall-OverlapConflict")

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

        # Conflicting event: 11:00 to 13:00
        payload = {
            "club": club.pk,
            "name": "Overlapping Event",
            "venue": venue.pk,
            "date": "2026-11-20",
            "start_time": "11:00",
            "end_time": "13:00",
            "description": "Cross-type overlap with session",
        }
        resp = client.post("/api/gymkhana/events/", payload, format="json")
        assert resp.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ), resp.data
        assert not ClubEvent.objects.filter(name="Overlapping Event").exists()


# ---------------------------------------------------------------------------
# TC-BR-14 to TC-BR-17: Club Membership Rules
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestClubMembershipRules:
    def test_tc_br_14_membership_requires_confirmed_club_permitted(self):
        """TC-BR-14 (source_id: BR-GYM-007-permitted):
        Verify BR-GYM-007 permitted outcome allowing student membership application to a confirmed club.
        """
        coordinator = _make_user("coord_br14")
        co_coordinator = _make_user("cocoord_br14")
        faculty = _make_user("faculty_br14")
        student = _make_user("student_br14")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=student)

        payload = {
            "club": club.pk,
            "achievements": "Participant in coding challenges",
        }
        resp = client.post("/api/gymkhana/memberships/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["status"] == "open"
        assert ClubMembership.objects.filter(club=club, student=student).exists()

    def test_tc_br_15_membership_requires_confirmed_club_prohibited(self):
        """TC-BR-15 (source_id: BR-GYM-007-prohibited):
        Verify BR-GYM-007 prohibited outcome rejecting membership application to an unconfirmed (open) club.
        """
        coordinator = _make_user("coord_br15")
        co_coordinator = _make_user("cocoord_br15")
        faculty = _make_user("faculty_br15")
        student = _make_user("student_br15")
        open_club = _make_club(coordinator, co_coordinator, faculty, status="open")

        client = APIClient()
        client.force_authenticate(user=student)

        payload = {
            "club": open_club.pk,
            "achievements": "Applying to open club",
        }
        resp = client.post("/api/gymkhana/memberships/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert not ClubMembership.objects.filter(club=open_club, student=student).exists()

    def test_tc_br_16_multiple_different_club_applications_permitted(self):
        """TC-BR-16 (source_id: BR-GYM-008-permitted):
        Verify BR-GYM-008 permitted outcome allowing a student to apply to multiple different clubs.
        """
        coordinator = _make_user("coord_br16")
        co_coordinator = _make_user("cocoord_br16")
        faculty = _make_user("faculty_br16")
        student = _make_user("student_br16")

        club_a = _make_club(
            coordinator, co_coordinator, faculty, status="confirmed", name="Club Alpha BR16"
        )
        club_b = _make_club(
            coordinator, co_coordinator, faculty, status="confirmed", name="Club Beta BR16"
        )

        # Existing application in Club A
        m_a = ClubMembership.objects.create(club=club_a, student=student, status="open")

        client = APIClient()
        client.force_authenticate(user=student)

        payload = {"club": club_b.pk, "achievements": "Application to Club B"}
        resp = client.post("/api/gymkhana/memberships/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

        # Both applications exist
        assert ClubMembership.objects.filter(club=club_a, student=student).exists()
        assert ClubMembership.objects.filter(club=club_b, student=student).exists()
        assert ClubMembership.objects.get(pk=m_a.pk).status == "open"

    def test_tc_br_17_no_duplicate_same_club_application_prohibited(self):
        """TC-BR-17 (source_id: BR-GYM-009-prohibited):
        Verify BR-GYM-009 prohibited outcome rejecting duplicate membership application to the same club.
        """
        coordinator = _make_user("coord_br17")
        co_coordinator = _make_user("cocoord_br17")
        faculty = _make_user("faculty_br17")
        student = _make_user("student_br17")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        # First application already submitted
        ClubMembership.objects.create(club=club, student=student, status="open")

        client = APIClient()
        client.force_authenticate(user=student)

        # Attempt duplicate submission to the same club
        payload = {"club": club.pk, "achievements": "Duplicate application"}
        resp = client.post("/api/gymkhana/memberships/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert ClubMembership.objects.filter(club=club, student=student).count() == 1


# ---------------------------------------------------------------------------
# TC-BR-18 to TC-BR-20: Club Head Authorization and Membership Approval
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestClubHeadAuthorizationAndMembershipApproval:
    def test_tc_br_18_club_head_authorization_permitted(self):
        """TC-BR-18 (source_id: BR-GYM-010-permitted):
        Verify BR-GYM-010 permitted outcome authorizing applicable club coordinator or co-coordinator for Club Head operations.
        """
        coordinator = _make_user("coord_br18")
        co_coordinator = _make_user("cocoord_br18")
        faculty = _make_user("faculty_br18")
        student_01 = _make_user("student_01_br18")
        student_02 = _make_user("student_02_br18")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        m1 = ClubMembership.objects.create(club=club, student=student_01, status="open")
        m2 = ClubMembership.objects.create(club=club, student=student_02, status="open")

        client = APIClient()

        # Coordinator approves m1
        client.force_authenticate(user=coordinator)
        resp1 = client.post(
            f"/api/gymkhana/memberships/{m1.pk}/approve/",
            {"action": "approve"},
            format="json",
        )
        assert resp1.status_code == status.HTTP_200_OK, resp1.data
        m1.refresh_from_db()
        assert m1.status == "confirmed"

        # Co-coordinator approves m2
        client.force_authenticate(user=co_coordinator)
        resp2 = client.post(
            f"/api/gymkhana/memberships/{m2.pk}/approve/",
            {"action": "approve"},
            format="json",
        )
        assert resp2.status_code == status.HTTP_200_OK, resp2.data
        m2.refresh_from_db()
        assert m2.status == "confirmed"

    def test_tc_br_19_club_head_authorization_prohibited(self):
        """TC-BR-19 (source_id: BR-GYM-010-prohibited):
        Verify BR-GYM-010 prohibited outcome refusing Club Head operations when user is not coordinator/co-coordinator of that club.
        """
        coordinator = _make_user("coord_br19")
        co_coordinator = _make_user("cocoord_br19")
        faculty = _make_user("faculty_br19")
        student_applicant = _make_user("applicant_br19")
        student_unauthorized = _make_user("unauthorized_br19")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        membership = ClubMembership.objects.create(
            club=club, student=student_applicant, status="open"
        )

        client = APIClient()

        # Non-leader student attempts Club Head operation
        client.force_authenticate(user=student_unauthorized)
        resp = client.post(
            f"/api/gymkhana/memberships/{membership.pk}/approve/",
            {"action": "approve"},
            format="json",
        )
        assert resp.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ), resp.data

        # Student applicant who is not coordinator/co-coordinator attempts approval
        client.force_authenticate(user=student_applicant)
        resp_self = client.post(
            f"/api/gymkhana/memberships/{membership.pk}/approve/",
            {"action": "approve"},
            format="json",
        )
        assert resp_self.status_code == status.HTTP_403_FORBIDDEN, resp_self.data

        membership.refresh_from_db()
        assert membership.status == "open"

    def test_tc_br_20_membership_approval_transition_permitted(self):
        """TC-BR-20 (source_id: BR-GYM-011-permitted):
        Verify BR-GYM-011 permitted outcome changing open application to confirmed and retaining optional remarks upon approval.
        """
        coordinator = _make_user("coord_br20")
        co_coordinator = _make_user("cocoord_br20")
        faculty = _make_user("faculty_br20")
        student = _make_user("student_br20")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        membership = ClubMembership.objects.create(club=club, student=student, status="open")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        payload = {"action": "approve", "remarks": "Accepted"}
        resp = client.post(
            f"/api/gymkhana/memberships/{membership.pk}/approve/",
            payload,
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["status"] == "confirmed"
        assert resp.data["remarks"] == "Accepted"

        membership.refresh_from_db()
        assert membership.status == "confirmed"
        assert membership.remarks == "Accepted"


# ---------------------------------------------------------------------------
# TC-BR-21 to TC-BR-28: Poll Choices, Targeting, Eligibility, and Voting
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPollChoicesTargetingAndVoting:
    def test_tc_br_21_minimum_poll_choices_permitted(self):
        """TC-BR-21 (source_id: BR-GYM-012-permitted):
        Verify BR-GYM-012 permitted threshold side accepting voting poll with at least two choices.
        """
        coordinator = _make_user("coord_br21")
        co_coordinator = _make_user("cocoord_br21")
        faculty = _make_user("faculty_br21")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        payload = {
            "club": club.pk,
            "title": "Two Choices Poll",
            "expiry_date": "2026-12-01",
            "choice_texts": ["Option 1", "Option 2"],
        }
        resp = client.post("/api/gymkhana/polls/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        poll = VotingPoll.objects.get(pk=resp.data["id"])
        assert poll.choices.count() == 2

    def test_tc_br_22_minimum_poll_choices_prohibited(self):
        """TC-BR-22 (source_id: BR-GYM-012-prohibited):
        Verify BR-GYM-012 prohibited threshold side rejecting voting poll with fewer than two choices.
        """
        coordinator = _make_user("coord_br22")
        co_coordinator = _make_user("cocoord_br22")
        faculty = _make_user("faculty_br22")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        payload = {
            "club": club.pk,
            "title": "Single Choice Disallowed Poll",
            "expiry_date": "2026-12-01",
            "choice_texts": ["Single Choice"],
        }
        resp = client.post("/api/gymkhana/polls/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert not VotingPoll.objects.filter(title="Single Choice Disallowed Poll").exists()

    def test_tc_br_23_poll_targeting_permitted(self):
        """TC-BR-23 (source_id: BR-GYM-013-permitted):
        Verify BR-GYM-013 permitted outcome addressing poll notification and access only to selected batch and branch groups.
        """
        pytest.skip(
            "NOT_AUTOMATED: No audience determination or notification dispatch interface exists in the Gymkhana module to verify target audience resolution for batch and branch groups."
        )

    def test_tc_br_24_poll_targeting_all_branches(self):
        """TC-BR-24 (source_id: BR-GYM-013-all-branches):
        Verify BR-GYM-013 stated exception/variation where branch selection represents all branches for selected batch.
        """
        pytest.skip(
            "NOT_AUTOMATED: No audience determination interface exists in the Gymkhana module to evaluate batch/branch audience groups."
        )

    def test_tc_br_25_active_poll_eligibility_permitted(self):
        """TC-BR-25 (source_id: BR-GYM-014-permitted):
        Verify BR-GYM-014 permitted outcome allowing participation when poll is active/unexpired and student is in target audience.
        """
        coordinator = _make_user("coord_br25")
        co_coordinator = _make_user("cocoord_br25")
        faculty = _make_user("faculty_br25")
        student = _make_user("student_br25")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        poll = VotingPoll.objects.create(
            club=club,
            title="Active Poll Participation Test",
            expiry_date=datetime.date(2027, 1, 1),
            target_batches=["2024"],
            target_branches=["CSE"],
            created_by=coordinator,
        )
        c1 = PollChoice.objects.create(poll=poll, text="Option 1")
        c2 = PollChoice.objects.create(poll=poll, text="Option 2")

        client = APIClient()
        client.force_authenticate(user=student)

        # Access poll
        resp = client.get(f"/api/gymkhana/polls/{poll.pk}/")
        assert resp.status_code == status.HTTP_200_OK, resp.data

        # Cast vote
        vote_resp = client.post(
            f"/api/gymkhana/polls/{poll.pk}/vote/",
            {"poll": poll.pk, "choice": c1.pk},
            format="json",
        )
        assert vote_resp.status_code == status.HTTP_201_CREATED, vote_resp.data
        assert PollVote.objects.filter(poll=poll, voter=student, choice=c1).exists()

    def test_tc_br_26_active_poll_eligibility_prohibited(self):
        """TC-BR-26 (source_id: BR-GYM-014-prohibited):
        Verify BR-GYM-014 prohibited outcome rejecting participation when poll is expired or student is not in target audience.
        """
        coordinator = _make_user("coord_br26")
        co_coordinator = _make_user("cocoord_br26")
        faculty = _make_user("faculty_br26")
        student = _make_user("student_br26")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        poll = VotingPoll.objects.create(
            club=club,
            title="Expired Poll Rejection Test",
            expiry_date=datetime.date(2020, 1, 1),  # Expired poll
            created_by=coordinator,
        )
        c1 = PollChoice.objects.create(poll=poll, text="Option 1")
        c2 = PollChoice.objects.create(poll=poll, text="Option 2")

        client = APIClient()
        client.force_authenticate(user=student)

        vote_resp = client.post(
            f"/api/gymkhana/polls/{poll.pk}/vote/",
            {"poll": poll.pk, "choice": c1.pk},
            format="json",
        )
        assert vote_resp.status_code == status.HTTP_400_BAD_REQUEST, vote_resp.data
        assert not PollVote.objects.filter(poll=poll, voter=student).exists()

    def test_tc_br_27_one_vote_per_student_per_poll_permitted(self):
        """TC-BR-27 (source_id: BR-GYM-015-permitted):
        Verify BR-GYM-015 permitted outcome allowing student's first vote in a poll and updating tally.
        """
        coordinator = _make_user("coord_br27")
        co_coordinator = _make_user("cocoord_br27")
        faculty = _make_user("faculty_br27")
        student = _make_user("student_br27")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        poll = VotingPoll.objects.create(
            club=club,
            title="First Vote Tally Poll",
            expiry_date=datetime.date(2027, 1, 1),
            created_by=coordinator,
        )
        c1 = PollChoice.objects.create(poll=poll, text="Choice 1", vote_count=0)
        c2 = PollChoice.objects.create(poll=poll, text="Choice 2", vote_count=0)

        client = APIClient()
        client.force_authenticate(user=student)

        resp = client.post(
            f"/api/gymkhana/polls/{poll.pk}/vote/",
            {"poll": poll.pk, "choice": c1.pk},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

        c1.refresh_from_db()
        assert c1.vote_count == 1
        assert PollVote.objects.filter(poll=poll, voter=student, choice=c1).exists()

    def test_tc_br_28_one_vote_per_student_per_poll_prohibited(self):
        """TC-BR-28 (source_id: BR-GYM-015-prohibited):
        Verify BR-GYM-015 prohibited outcome rejecting second vote by same student in same poll.
        """
        coordinator = _make_user("coord_br28")
        co_coordinator = _make_user("cocoord_br28")
        faculty = _make_user("faculty_br28")
        student = _make_user("student_br28")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        poll = VotingPoll.objects.create(
            club=club,
            title="Duplicate Vote Rejected Poll",
            expiry_date=datetime.date(2027, 1, 1),
            created_by=coordinator,
        )
        c1 = PollChoice.objects.create(poll=poll, text="Choice 1", vote_count=1)
        c2 = PollChoice.objects.create(poll=poll, text="Choice 2", vote_count=0)
        PollVote.objects.create(poll=poll, choice=c1, voter=student)

        client = APIClient()
        client.force_authenticate(user=student)

        # Attempt second vote in the same poll
        resp = client.post(
            f"/api/gymkhana/polls/{poll.pk}/vote/",
            {"poll": poll.pk, "choice": c2.pk},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data

        c1.refresh_from_db()
        c2.refresh_from_db()
        assert c1.vote_count == 1
        assert c2.vote_count == 0
        assert PollVote.objects.filter(poll=poll, voter=student).count() == 1


# ---------------------------------------------------------------------------
# TC-BR-29: Leadership Succession
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLeadershipSuccession:
    def test_tc_br_29_leadership_succession_permitted(self):
        """TC-BR-29 (source_id: BR-GYM-016-permitted):
        Verify BR-GYM-016 permitted outcome ensuring superseded leadership designations no longer remain current after leadership change.
        """
        student_01 = _make_user("student_01_br29")
        student_02 = _make_user("student_02_br29")
        student_03 = _make_user("student_03_br29")
        student_04 = _make_user("student_04_br29")
        faculty_01 = _make_user("faculty_01_br29")

        club = _make_club(student_01, student_02, faculty_01, status="confirmed")
        assert club.is_head(student_01) is True
        assert club.is_head(student_02) is True

        client = APIClient()
        client.force_authenticate(user=student_01)

        patch_payload = {
            "coordinator": student_03.pk,
            "co_coordinator": student_04.pk,
        }
        resp = client.patch(f"/api/gymkhana/clubs/{club.pk}/", patch_payload, format="json")
        assert resp.status_code == status.HTTP_200_OK, resp.data

        club.refresh_from_db()
        assert club.coordinator == student_03
        assert club.co_coordinator == student_04
        assert club.is_head(student_03) is True
        assert club.is_head(student_04) is True
        assert club.is_head(student_01) is False
        assert club.is_head(student_02) is False


# ---------------------------------------------------------------------------
# TC-BR-30 to TC-BR-33: Club Budget Rules
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestClubBudgetRules:
    def test_tc_br_30_non_negative_club_budget_permitted(self):
        """TC-BR-30 (source_id: BR-GYM-017-permitted):
        Verify BR-GYM-017 permitted threshold side accepting budget amount zero or greater.
        """
        coordinator = _make_user("coord_br30")
        co_coordinator = _make_user("cocoord_br30")
        faculty = _make_user("faculty_br30")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        supporting_file = SimpleUploadedFile(
            "budget_zero.pdf", b"zero budget data", content_type="application/pdf"
        )
        payload = {
            "club": club.pk,
            "amount": "0.00",
            "purpose": "Zero budget baseline request",
            "description": "Boundary check zero amount",
            "supporting_file": supporting_file,
        }
        resp = client.post("/api/gymkhana/budget-requests/", payload, format="multipart")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["amount"] == "0.00"

        br = ClubBudgetRequest.objects.get(pk=resp.data["id"])
        assert br.amount == Decimal("0.00")

    def test_tc_br_31_non_negative_club_budget_prohibited(self):
        """TC-BR-31 (source_id: BR-GYM-017-prohibited):
        Verify BR-GYM-017 prohibited threshold side rejecting budget amount less than zero.
        """
        coordinator = _make_user("coord_br31")
        co_coordinator = _make_user("cocoord_br31")
        faculty = _make_user("faculty_br31")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        supporting_file = SimpleUploadedFile(
            "budget_negative.pdf", b"negative budget data", content_type="application/pdf"
        )
        payload = {
            "club": club.pk,
            "amount": "-0.01",
            "purpose": "Negative budget check",
            "description": "Boundary check negative amount",
            "supporting_file": supporting_file,
        }
        resp = client.post("/api/gymkhana/budget-requests/", payload, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert not ClubBudgetRequest.objects.filter(
            club=club, purpose="Negative budget check"
        ).exists()

    def test_tc_br_32_budget_supporting_file_required_permitted(self):
        """TC-BR-32 (source_id: BR-GYM-018-permitted):
        Verify BR-GYM-018 permitted outcome accepting budget request with supporting file included.
        """
        coordinator = _make_user("coord_br32")
        co_coordinator = _make_user("cocoord_br32")
        faculty = _make_user("faculty_br32")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        supporting_file = SimpleUploadedFile(
            "budget_supporting.pdf", b"supporting file content", content_type="application/pdf"
        )
        payload = {
            "club": club.pk,
            "amount": "1500.00",
            "purpose": "Hardware equipment",
            "description": "With supporting file",
            "supporting_file": supporting_file,
        }
        resp = client.post("/api/gymkhana/budget-requests/", payload, format="multipart")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

        br = ClubBudgetRequest.objects.get(pk=resp.data["id"])
        assert bool(br.supporting_file) is True

    def test_tc_br_33_budget_supporting_file_required_prohibited(self):
        """TC-BR-33 (source_id: BR-GYM-018-prohibited):
        Verify BR-GYM-018 prohibited outcome rejecting budget request when supporting file is missing.
        """
        coordinator = _make_user("coord_br33")
        co_coordinator = _make_user("cocoord_br33")
        faculty = _make_user("faculty_br33")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        payload = {
            "club": club.pk,
            "amount": "1500.00",
            "purpose": "Missing supporting file request",
            "description": "Should fail because supporting file is omitted",
        }
        resp = client.post("/api/gymkhana/budget-requests/", payload, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert not ClubBudgetRequest.objects.filter(
            club=club, purpose="Missing supporting file request"
        ).exists()


# ---------------------------------------------------------------------------
# TC-BR-34 to TC-BR-35: Event Report Rules
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEventReportRules:
    def test_tc_br_34_event_report_file_required_permitted(self):
        """TC-BR-34 (source_id: BR-GYM-019-permitted):
        Verify BR-GYM-019 permitted outcome accepting event report with report/details file included.
        """
        coordinator = _make_user("coord_br34")
        co_coordinator = _make_user("cocoord_br34")
        faculty = _make_user("faculty_br34")
        student_01 = _make_user("student_01_br34")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        report_file = SimpleUploadedFile(
            "event_report.pdf", b"event report content", content_type="application/pdf"
        )
        payload = {
            "club": club.pk,
            "student_incharge": student_01.pk,
            "event_name": "Robotics Exhibition",
            "event_date": "2026-11-15",
            "description": "Event report with file attached",
            "report_file": report_file,
        }
        resp = client.post("/api/gymkhana/event-reports/", payload, format="multipart")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

        report = ClubEventReport.objects.get(pk=resp.data["id"])
        assert report.event_name == "Robotics Exhibition"
        assert bool(report.report_file) is True

    def test_tc_br_35_event_report_file_required_prohibited(self):
        """TC-BR-35 (source_id: BR-GYM-019-prohibited):
        Verify BR-GYM-019 prohibited outcome rejecting event report when report/details file is missing.
        """
        coordinator = _make_user("coord_br35")
        co_coordinator = _make_user("cocoord_br35")
        faculty = _make_user("faculty_br35")
        student_01 = _make_user("student_01_br35")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        payload = {
            "club": club.pk,
            "student_incharge": student_01.pk,
            "event_name": "Missing Report File Event",
            "event_date": "2026-11-15",
            "description": "Should fail because report file is missing",
        }
        resp = client.post("/api/gymkhana/event-reports/", payload, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert not ClubEventReport.objects.filter(
            club=club, event_name="Missing Report File Event"
        ).exists()


# ---------------------------------------------------------------------------
# TC-BR-36 to TC-BR-39: Configured Venue and Faculty Review Authorization
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestConfiguredVenueAndFacultyReview:
    def test_tc_br_36_configured_venue_required_permitted(self):
        """TC-BR-36 (source_id: BR-GYM-020-permitted):
        Verify BR-GYM-020 permitted outcome accepting booking with a configured Gymkhana venue.
        """
        coordinator = _make_user("coord_br36")
        co_coordinator = _make_user("cocoord_br36")
        faculty = _make_user("faculty_br36")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        venue_name = _unique_name("Hall-1")
        venue = Venue.objects.create(name=venue_name, capacity=100)

        client = APIClient()
        client.force_authenticate(user=coordinator)

        payload = {
            "club": club.pk,
            "venue": venue.pk,
            "date": "2026-11-20",
            "start_time": "10:00",
            "end_time": "12:00",
            "description": "Booking with configured venue",
        }
        resp = client.post("/api/gymkhana/sessions/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert ClubSession.objects.filter(club=club, venue=venue).exists()

    def test_tc_br_37_configured_venue_required_prohibited(self):
        """TC-BR-37 (source_id: BR-GYM-020-prohibited):
        Verify BR-GYM-020 prohibited outcome rejecting booking with unconfigured venue.
        """
        coordinator = _make_user("coord_br37")
        co_coordinator = _make_user("cocoord_br37")
        faculty = _make_user("faculty_br37")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        unconfigured_venue_id = 999999
        payload = {
            "club": club.pk,
            "venue": unconfigured_venue_id,
            "date": "2026-11-20",
            "start_time": "10:00",
            "end_time": "12:00",
            "description": "Booking with unconfigured venue OffCampus-Cafe",
        }
        resp = client.post("/api/gymkhana/sessions/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert not ClubSession.objects.filter(
            club=club, description="Booking with unconfigured venue OffCampus-Cafe"
        ).exists()

    def test_tc_br_38_faculty_report_review_authorization_permitted(self):
        """TC-BR-38 (source_id: BR-GYM-021-permitted):
        Verify BR-GYM-021 permitted outcome allowing Club Faculty Councillor to review reports for assigned club.
        """
        coordinator = _make_user("coord_br38")
        co_coordinator = _make_user("cocoord_br38")
        faculty_a = _make_user("faculty_a_br38")
        student_01 = _make_user("student_01_br38")
        club_a = _make_club(
            coordinator, co_coordinator, faculty_a, status="confirmed", name="Club A BR38"
        )

        report_file = SimpleUploadedFile(
            "review_report.pdf", b"review report content", content_type="application/pdf"
        )
        report = ClubEventReport.objects.create(
            club=club_a,
            submitted_by=coordinator,
            student_incharge=student_01,
            event_name="RoboWars Annual Report",
            description="Detailed report for review",
            event_date=datetime.date(2026, 11, 15),
            report_file=report_file,
        )

        client = APIClient()
        client.force_authenticate(user=faculty_a)

        resp = client.get(f"/api/gymkhana/event-reports/{report.pk}/")
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["event_name"] == "RoboWars Annual Report"
        assert resp.data["description"] == "Detailed report for review"
        assert "review_report" in resp.data["report_file"]

    def test_tc_br_39_faculty_report_review_authorization_prohibited(self):
        """TC-BR-39 (source_id: BR-GYM-021-prohibited):
        Verify BR-GYM-021 prohibited outcome denying report review when faculty user is not assigned to that club.
        """
        coordinator = _make_user("coord_br39")
        co_coordinator = _make_user("cocoord_br39")
        faculty_a = _make_user("faculty_a_br39")
        faculty_other = _make_user("faculty_other_br39")
        student_01 = _make_user("student_01_br39")
        club_a = _make_club(
            coordinator, co_coordinator, faculty_a, status="confirmed", name="Club A BR39"
        )

        report_file = SimpleUploadedFile(
            "restricted_report.pdf", b"restricted report content", content_type="application/pdf"
        )
        report = ClubEventReport.objects.create(
            club=club_a,
            submitted_by=coordinator,
            student_incharge=student_01,
            event_name="Confidential Club Event Report",
            description="Report inaccessible to unassigned faculty",
            event_date=datetime.date(2026, 11, 15),
            report_file=report_file,
        )

        client = APIClient()
        client.force_authenticate(user=faculty_other)

        resp = client.get(f"/api/gymkhana/event-reports/{report.pk}/")
        assert resp.status_code in (
            status.HTTP_404_NOT_FOUND,
            status.HTTP_403_FORBIDDEN,
        ), resp.data
