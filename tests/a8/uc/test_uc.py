"""Automated backend test suite for Gymkhana Use Cases (UC).

Generated from a8_design/UC_DESIGN.json.
Rules applied:
- Implement exactly the supplied test cases (TC-UC-01 to TC-UC-30).
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
# TC-UC-01 to TC-UC-03: UC-GYM-001 Club Creation & Lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestClubCreationAndLifecycle:
    def test_tc_uc_01_create_new_club_main_flow(self):
        """TC-UC-01 (source_id: UC-GYM-001 Main Flow):
        Verify main success scenario for creating a new club by Student Admin.
        """
        student_admin = _make_user("admin_uc01", is_staff=True)
        student_01 = _make_user("student_01_uc01")
        student_02 = _make_user("student_02_uc01")
        faculty_01 = _make_user("faculty_01_uc01")

        client = APIClient()
        client.force_authenticate(user=student_admin)

        club_name = _unique_name("Astronomy Club")
        payload = {
            "name": club_name,
            "description": "Stargazing club",
            "category": "technical",
            "coordinator": student_01.pk,
            "co_coordinator": student_02.pk,
            "faculty_councillor": faculty_01.pk,
        }
        resp = client.post("/api/gymkhana/clubs/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["status"] == "open"
        assert resp.data["name"] == club_name
        assert resp.data["category"] == "technical"
        assert resp.data["coordinator"] == student_01.pk
        assert resp.data["co_coordinator"] == student_02.pk
        assert resp.data["faculty_councillor"] == faculty_01.pk
        assert resp.data["description"] == "Stargazing club"

        club = Club.objects.get(name=club_name)
        assert club.status == "open"

    def test_tc_uc_02_create_club_invalid_leader_correction_alternative_flow(self):
        """TC-UC-02 (source_id: UC-GYM-001 Alternative Flow):
        Verify alternative flow where an invalid leader or faculty assignment is identified
        and allows correction without creating the club.
        """
        student_admin = _make_user("admin_uc02", is_staff=True)
        student_01 = _make_user("student_01_uc02")
        student_02 = _make_user("student_02_uc02")
        faculty_01 = _make_user("faculty_01_uc02")

        client = APIClient()
        client.force_authenticate(user=student_admin)

        club_name = _unique_name("Astronomy Club")
        invalid_coordinator_id = 999999
        payload = {
            "name": club_name,
            "description": "Stargazing club",
            "category": "technical",
            "coordinator": invalid_coordinator_id,
            "co_coordinator": student_02.pk,
            "faculty_councillor": faculty_01.pk,
        }

        # Step 1: Submit with invalid coordinator -> flagged without creating club
        resp_invalid = client.post("/api/gymkhana/clubs/", payload, format="json")
        assert resp_invalid.status_code == status.HTTP_400_BAD_REQUEST, resp_invalid.data
        assert not Club.objects.filter(name=club_name).exists()

        # Step 2: Correct to valid student ID and resubmit
        payload["coordinator"] = student_01.pk
        resp_valid = client.post("/api/gymkhana/clubs/", payload, format="json")
        assert resp_valid.status_code == status.HTTP_201_CREATED, resp_valid.data
        assert resp_valid.data["status"] == "open"
        assert Club.objects.filter(name=club_name, status="open").exists()

    def test_tc_uc_03_create_club_storage_failure_exception_flow(self):
        """TC-UC-03 (source_id: UC-GYM-001 Exception Flow):
        Verify exception flow when required club data cannot be stored, club is not created,
        and system reports failure.
        """
        student_admin = _make_user("admin_uc03", is_staff=True)
        student_01 = _make_user("student_01_uc03")
        student_02 = _make_user("student_02_uc03")
        faculty_01 = _make_user("faculty_01_uc03")

        # Existing club violates unique name constraint
        existing_club = _make_club(
            student_01, student_02, faculty_01, name=_unique_name("UniqueAstronomyClub")
        )

        client = APIClient()
        client.force_authenticate(user=student_admin)

        payload = {
            "name": existing_club.name,  # Mandatory unique constraint violated
            "description": "Attempting duplicate club name",
            "category": "technical",
            "coordinator": student_01.pk,
            "co_coordinator": student_02.pk,
            "faculty_councillor": faculty_01.pk,
        }
        resp = client.post("/api/gymkhana/clubs/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        # Ensure no partial or duplicate record is created
        assert Club.objects.filter(name=existing_club.name).count() == 1


# ---------------------------------------------------------------------------
# TC-UC-04 to TC-UC-06: UC-GYM-002 Session Booking
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSessionBooking:
    def test_tc_uc_04_book_club_session_main_flow(self):
        """TC-UC-04 (source_id: UC-GYM-002 Main Flow):
        Verify main success scenario for booking a club session by Club Head without scheduling conflict.
        """
        coordinator = _make_user("coord_uc04")
        co_coordinator = _make_user("cocoord_uc04")
        faculty = _make_user("faculty_uc04")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")
        venue = _make_venue("Studio-1")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        poster = SimpleUploadedFile("jam.png", b"fake poster image", content_type="image/png")
        payload = {
            "club": club.pk,
            "venue": venue.pk,
            "date": "2026-11-22",
            "start_time": "16:00",
            "end_time": "18:00",
            "description": "Weekly Jam",
            "poster": poster,
        }
        resp = client.post("/api/gymkhana/sessions/", payload, format="multipart")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert ClubSession.objects.filter(
            club=club,
            venue=venue,
            date=datetime.date(2026, 11, 22),
            start_time=datetime.time(16, 0),
            end_time=datetime.time(18, 0),
        ).exists()
        # Note: Recipient notification interface is not present in the Gymkhana module.

    def test_tc_uc_05_book_club_session_slot_overlap_alternative_flow(self):
        """TC-UC-05 (source_id: UC-GYM-002 Alternative Flow):
        Verify alternative flow when requested session slot overlaps an existing session or event,
        system rejects booking and prompts for another slot.
        """
        coordinator = _make_user("coord_uc05")
        co_coordinator = _make_user("cocoord_uc05")
        faculty = _make_user("faculty_uc05")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")
        venue = _make_venue("Studio-1")

        # Existing booking occupies 'Studio-1' on '2026-11-22' from '16:00' to '18:00'
        ClubSession.objects.create(
            club=club,
            venue=venue,
            date=datetime.date(2026, 11, 22),
            start_time=datetime.time(16, 0),
            end_time=datetime.time(18, 0),
            created_by=coordinator,
        )

        client = APIClient()
        client.force_authenticate(user=coordinator)

        # Club Head attempts booking for same venue/date from '17:00' to '19:00'
        payload = {
            "club": club.pk,
            "venue": venue.pk,
            "date": "2026-11-22",
            "start_time": "17:00",
            "end_time": "19:00",
            "description": "Overlapping Session",
        }
        resp = client.post("/api/gymkhana/sessions/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert not ClubSession.objects.filter(
            venue=venue,
            date=datetime.date(2026, 11, 22),
            start_time=datetime.time(17, 0),
        ).exists()

    def test_tc_uc_06_book_club_session_invalid_input_exception_flow(self):
        """TC-UC-06 (source_id: UC-GYM-002 Exception Flow):
        Verify exception flow when venue is invalid, time range is invalid, or processing fails,
        no booking is recorded.
        """
        coordinator = _make_user("coord_uc06")
        co_coordinator = _make_user("cocoord_uc06")
        faculty = _make_user("faculty_uc06")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")
        venue = _make_venue("Studio-1")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        # Invalid time range: start_time='18:00', end_time='16:00'
        payload_invalid_time = {
            "club": club.pk,
            "venue": venue.pk,
            "date": "2026-11-22",
            "start_time": "18:00",
            "end_time": "16:00",
            "description": "Invalid time range",
        }
        resp = client.post("/api/gymkhana/sessions/", payload_invalid_time, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert not ClubSession.objects.filter(
            club=club,
            start_time=datetime.time(18, 0),
            end_time=datetime.time(16, 0),
        ).exists()


# ---------------------------------------------------------------------------
# TC-UC-07 to TC-UC-09: UC-GYM-003 Event Booking
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEventBooking:
    def test_tc_uc_07_book_club_event_main_flow(self):
        """TC-UC-07 (source_id: UC-GYM-003 Main Flow):
        Verify main success scenario for booking a club event by Club Head.
        """
        coordinator = _make_user("coord_uc07")
        co_coordinator = _make_user("cocoord_uc07")
        faculty = _make_user("faculty_uc07")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")
        venue = _make_venue("Auditorium")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        poster = SimpleUploadedFile("hack.jpg", b"fake poster image", content_type="image/jpeg")
        payload = {
            "club": club.pk,
            "name": "HackFusion",
            "faculty_councillor": faculty.pk,
            "venue": venue.pk,
            "date": "2026-11-28",
            "start_time": "09:00",
            "end_time": "17:00",
            "poster": poster,
            "description": "Hackathon",
        }
        resp = client.post("/api/gymkhana/events/", payload, format="multipart")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert ClubEvent.objects.filter(
            club=club,
            name="HackFusion",
            venue=venue,
            date=datetime.date(2026, 11, 28),
            start_time=datetime.time(9, 0),
            end_time=datetime.time(17, 0),
        ).exists()
        # Note: Recipient notification interface is not present in the Gymkhana module.

    def test_tc_uc_08_book_club_event_cross_type_slot_overlap_alternative_flow(self):
        """TC-UC-08 (source_id: UC-GYM-003 Alternative Flow):
        Verify alternative flow when requested event slot overlaps an existing session or event,
        system rejects booking and prompts for another slot.
        """
        coordinator = _make_user("coord_uc08")
        co_coordinator = _make_user("cocoord_uc08")
        faculty = _make_user("faculty_uc08")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")
        venue = _make_venue("Auditorium")

        # Existing session booked in 'Auditorium' on '2026-11-28' from '10:00' to '12:00'
        ClubSession.objects.create(
            club=club,
            venue=venue,
            date=datetime.date(2026, 11, 28),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(12, 0),
            created_by=coordinator,
        )

        client = APIClient()
        client.force_authenticate(user=coordinator)

        # Club Head attempts event booking in 'Auditorium' on '2026-11-28' from '11:00' to '15:00'
        payload = {
            "club": club.pk,
            "name": "Overlapping Hackathon",
            "venue": venue.pk,
            "date": "2026-11-28",
            "start_time": "11:00",
            "end_time": "15:00",
            "description": "Cross-type conflict",
        }
        resp = client.post("/api/gymkhana/events/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert not ClubEvent.objects.filter(
            venue=venue,
            date=datetime.date(2026, 11, 28),
            start_time=datetime.time(11, 0),
        ).exists()

    def test_tc_uc_09_book_club_event_invalid_faculty_reference_exception_flow(self):
        """TC-UC-09 (source_id: UC-GYM-003 Exception Flow):
        Verify exception flow when venue, faculty reference, or time range is invalid,
        no successful event booking is recorded.
        """
        coordinator = _make_user("coord_uc09")
        co_coordinator = _make_user("cocoord_uc09")
        faculty = _make_user("faculty_uc09")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")
        venue = _make_venue("Auditorium")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        payload = {
            "club": club.pk,
            "name": _unique_name("EventInvalidFaculty"),
            "faculty_councillor": "non_existent_faculty",
            "venue": venue.pk,
            "date": "2026-11-28",
            "start_time": "09:00",
            "end_time": "17:00",
            "description": "Event with invalid faculty reference",
        }
        resp = client.post("/api/gymkhana/events/", payload, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, (
            f"Expected rejection with validation error for invalid faculty councillor reference, got {resp.status_code}: {resp.data}"
        )
        assert not ClubEvent.objects.filter(club=club, name=payload["name"]).exists()


# ---------------------------------------------------------------------------
# TC-UC-10 to TC-UC-12: UC-GYM-004 Membership Application
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestClubMembershipApplication:
    def test_tc_uc_10_apply_membership_main_flow(self):
        """TC-UC-10 (source_id: UC-GYM-004 Main Flow):
        Verify main success scenario where student applies for membership in a confirmed club.
        """
        coordinator = _make_user("coord_uc10")
        co_coordinator = _make_user("cocoord_uc10")
        faculty = _make_user("faculty_uc10")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")
        student = _make_user("student_uc10")

        client = APIClient()
        client.force_authenticate(user=student)

        payload = {
            "club": club.pk,
            "achievements": "Interested in robotics workshops",
        }
        resp = client.post("/api/gymkhana/memberships/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["status"] == "open"
        assert resp.data["club"] == club.pk
        assert ClubMembership.objects.filter(club=club, student=student, status="open").exists()

    def test_tc_uc_11_apply_membership_different_club_alternative_flow(self):
        """TC-UC-11 (source_id: UC-GYM-004 Alternative Flow):
        Verify alternative flow where student applies to another different club when applications
        to other clubs exist.
        """
        coordinator = _make_user("coord_uc11")
        co_coordinator = _make_user("cocoord_uc11")
        faculty = _make_user("faculty_uc11")
        club_a = _make_club(coordinator, co_coordinator, faculty, status="confirmed", name="Club Alpha")
        club_b = _make_club(coordinator, co_coordinator, faculty, status="confirmed", name="Club Beta")
        student = _make_user("student_uc11")

        # Student has an active open application to Club A
        app_a = ClubMembership.objects.create(club=club_a, student=student, status="open")

        client = APIClient()
        client.force_authenticate(user=student)

        # Student submits membership application to Club B
        resp = client.post("/api/gymkhana/memberships/", {"club": club_b.pk}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["status"] == "open"
        assert resp.data["club"] == club_b.pk

        # Previous application to Club A remains unchanged with status 'open'
        app_a.refresh_from_db()
        assert app_a.status == "open"
        assert ClubMembership.objects.filter(club=club_b, student=student, status="open").exists()

    def test_tc_uc_12_apply_membership_duplicate_exception_flow(self):
        """TC-UC-12 (source_id: UC-GYM-004 Exception Flow):
        Verify exception flow when duplicate same-club application is detected,
        duplicate is rejected and existing application is left unchanged.
        """
        coordinator = _make_user("coord_uc12")
        co_coordinator = _make_user("cocoord_uc12")
        faculty = _make_user("faculty_uc12")
        club_a = _make_club(coordinator, co_coordinator, faculty, status="confirmed")
        student = _make_user("student_uc12")

        # Existing application on record for Club A
        existing_app = ClubMembership.objects.create(
            club=club_a, student=student, status="open", achievements="First application"
        )

        client = APIClient()
        client.force_authenticate(user=student)

        # Student attempts to submit another membership application for Club A
        resp = client.post(
            "/api/gymkhana/memberships/",
            {"club": club_a.pk, "achievements": "Duplicate attempt"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert ClubMembership.objects.filter(club=club_a, student=student).count() == 1
        existing_app.refresh_from_db()
        assert existing_app.achievements == "First application"
        assert existing_app.status == "open"


# ---------------------------------------------------------------------------
# TC-UC-13 to TC-UC-15: UC-GYM-005 Membership Approval
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestClubMembershipApproval:
    def test_tc_uc_13_approve_membership_single_main_flow(self):
        """TC-UC-13 (source_id: UC-GYM-005 Main Flow):
        Verify main success scenario for approving a single pending club membership application by Club Head.
        """
        coordinator = _make_user("coord_uc13")
        co_coordinator = _make_user("cocoord_uc13")
        faculty = _make_user("faculty_uc13")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")
        student = _make_user("student_uc13")

        membership = ClubMembership.objects.create(club=club, student=student, status="open")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        payload = {
            "action": "approve",
            "remarks": "Accepted based on interview",
        }
        resp = client.post(f"/api/gymkhana/memberships/{membership.pk}/approve/", payload, format="json")
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["status"] == "confirmed"
        assert resp.data["remarks"] == "Accepted based on interview"

        membership.refresh_from_db()
        assert membership.status == "confirmed"
        assert membership.remarks == "Accepted based on interview"

    def test_tc_uc_14_approve_membership_batch_alternative_flow(self):
        """TC-UC-14 (source_id: UC-GYM-005 Alternative Flow):
        Verify alternative flow where Club Head approves multiple selected pending applications
        in one interaction, each evaluated independently.
        """
        coordinator = _make_user("coord_uc14")
        co_coordinator = _make_user("cocoord_uc14")
        faculty = _make_user("faculty_uc14")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        student_1 = _make_user("student_1_uc14")
        student_2 = _make_user("student_2_uc14")
        membership_1 = ClubMembership.objects.create(club=club, student=student_1, status="open")
        membership_2 = ClubMembership.objects.create(club=club, student=student_2, status="open")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        # Batch approval triggered for both open applications, each evaluated independently
        for mem in [membership_1, membership_2]:
            resp = client.post(
                f"/api/gymkhana/memberships/{mem.pk}/approve/",
                {"action": "approve", "remarks": "Approved in batch"},
                format="json",
            )
            assert resp.status_code == status.HTTP_200_OK, resp.data
            assert resp.data["status"] == "confirmed"

        membership_1.refresh_from_db()
        membership_2.refresh_from_db()
        assert membership_1.status == "confirmed"
        assert membership_2.status == "confirmed"

    def test_tc_uc_15_approve_membership_unauthorized_or_not_open_exception_flow(self):
        """TC-UC-15 (source_id: UC-GYM-005 Exception Flow):
        Verify exception flow when application is no longer open or does not belong to actor's club,
        it is not changed.
        """
        coord_a = _make_user("coord_a_uc15")
        coord_b = _make_user("coord_b_uc15")
        cocoord = _make_user("cocoord_uc15")
        faculty = _make_user("faculty_uc15")
        club_a = _make_club(coord_a, cocoord, faculty, status="confirmed", name="Club A")
        club_b = _make_club(coord_b, cocoord, faculty, status="confirmed", name="Club B")

        student_1 = _make_user("student_1_uc15")
        student_2 = _make_user("student_2_uc15")

        # Membership for Club B
        mem_b = ClubMembership.objects.create(club=club_b, student=student_1, status="open")
        # Membership for Club A already confirmed
        mem_a_confirmed = ClubMembership.objects.create(club=club_a, student=student_2, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=coord_a)

        # Case 1: Actor is Club Head of Club A, but application belongs to Club B
        resp_other_club = client.post(
            f"/api/gymkhana/memberships/{mem_b.pk}/approve/",
            {"action": "approve"},
            format="json",
        )
        assert resp_other_club.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ], resp_other_club.data
        mem_b.refresh_from_db()
        assert mem_b.status == "open"

        # Case 2: Application is already confirmed (not open)
        resp_already_confirmed = client.post(
            f"/api/gymkhana/memberships/{mem_a_confirmed.pk}/approve/",
            {"action": "approve"},
            format="json",
        )
        assert resp_already_confirmed.status_code == status.HTTP_400_BAD_REQUEST, resp_already_confirmed.data
        mem_a_confirmed.refresh_from_db()
        assert mem_a_confirmed.status == "confirmed"


# ---------------------------------------------------------------------------
# TC-UC-16 to TC-UC-18: UC-GYM-006 Voting Poll Creation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestVotingPollCreation:
    def test_tc_uc_16_create_voting_poll_main_flow(self):
        """TC-UC-16 (source_id: UC-GYM-006 Main Flow):
        Verify main success scenario for creating a voting poll with choices, expiry,
        target audience, and notifications.
        """
        coordinator = _make_user("coord_uc16")
        co_coordinator = _make_user("cocoord_uc16")
        faculty = _make_user("faculty_uc16")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        payload = {
            "club": club.pk,
            "title": "T-shirt design",
            "description": "Choose club tee",
            "expiry_date": "2026-12-10",
            "choice_texts": ["Design 1", "Design 2"],
            "target_batches": ["2023"],
            "target_branches": ["ECE"],
        }
        resp = client.post("/api/gymkhana/polls/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["title"] == "T-shirt design"
        assert resp.data["target_batches"] == ["2023"]
        assert resp.data["target_branches"] == ["ECE"]

        poll = VotingPoll.objects.get(pk=resp.data["id"])
        assert poll.choices.count() == 2
        assert set(poll.choices.values_list("text", flat=True)) == {"Design 1", "Design 2"}
        # Note: Target audience notification interface is not present in the Gymkhana module.

    def test_tc_uc_17_create_voting_poll_all_branches_alternative_flow(self):
        """TC-UC-17 (source_id: UC-GYM-006 Alternative Flow):
        Verify alternative flow where target branch selection represents all branches
        for a selected batch where configured.
        """
        coordinator = _make_user("coord_uc17")
        co_coordinator = _make_user("cocoord_uc17")
        faculty = _make_user("faculty_uc17")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        payload = {
            "club": club.pk,
            "title": _unique_name("Batch 2024 All Branches Poll"),
            "description": "Poll targeting all branches in batch 2024",
            "expiry_date": "2026-12-10",
            "choice_texts": ["Choice A", "Choice B"],
            "target_batches": ["2024"],
            "target_branches": ["ALL"],
        }
        resp = client.post("/api/gymkhana/polls/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["target_batches"] == ["2024"]
        assert resp.data["target_branches"] == ["ALL"]

        poll = VotingPoll.objects.get(pk=resp.data["id"])
        assert poll.choices.count() == 2

    def test_tc_uc_18_create_voting_poll_insufficient_choices_exception_flow(self):
        """TC-UC-18 (source_id: UC-GYM-006 Exception Flow):
        Verify exception flow when fewer than two choices are supplied or target information is invalid,
        poll is not created.
        """
        coordinator = _make_user("coord_uc18")
        co_coordinator = _make_user("cocoord_uc18")
        faculty = _make_user("faculty_uc18")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        # Poll with only 1 choice (< 2 choices)
        payload = {
            "club": club.pk,
            "title": _unique_name("Invalid Single Choice Poll"),
            "description": "Only 1 choice supplied",
            "expiry_date": "2026-12-10",
            "choice_texts": ["Only Option"],
            "target_batches": ["2023"],
            "target_branches": ["CSE"],
        }
        resp = client.post("/api/gymkhana/polls/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert not VotingPoll.objects.filter(title=payload["title"]).exists()


# ---------------------------------------------------------------------------
# TC-UC-19 to TC-UC-20: UC-GYM-007 Voting Poll Participation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestVotingPollVoting:
    def test_tc_uc_19_cast_vote_main_flow(self):
        """TC-UC-19 (source_id: UC-GYM-007 Main Flow):
        Verify main success scenario where eligible student views active poll and casts one vote.
        """
        coordinator = _make_user("coord_uc19")
        co_coordinator = _make_user("cocoord_uc19")
        faculty = _make_user("faculty_uc19")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")
        student = _make_user("student_uc19")

        poll = VotingPoll.objects.create(
            club=club,
            title="Active Poll",
            expiry_date=datetime.date.today() + datetime.timedelta(days=10),
            created_by=coordinator,
        )
        choice_a = PollChoice.objects.create(poll=poll, text="Choice A")
        choice_b = PollChoice.objects.create(poll=poll, text="Choice B")

        client = APIClient()
        client.force_authenticate(user=student)

        payload = {"poll": poll.pk, "choice": choice_a.pk}
        resp = client.post(f"/api/gymkhana/polls/{poll.pk}/vote/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

        choice_a.refresh_from_db()
        assert choice_a.vote_count == 1
        assert PollVote.objects.filter(poll=poll, voter=student, choice=choice_a).exists()

    def test_tc_uc_20_duplicate_vote_rejected_exception_flow(self):
        """TC-UC-20 (source_id: UC-GYM-007 Exception Flow):
        Verify exception flow when student has already voted, is not eligible, or poll is not active,
        vote is rejected and tally unchanged.
        """
        coordinator = _make_user("coord_uc20")
        co_coordinator = _make_user("cocoord_uc20")
        faculty = _make_user("faculty_uc20")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")
        student = _make_user("student_uc20")

        poll = VotingPoll.objects.create(
            club=club,
            title="Poll Already Voted",
            expiry_date=datetime.date.today() + datetime.timedelta(days=10),
            created_by=coordinator,
        )
        choice_a = PollChoice.objects.create(poll=poll, text="Choice A", vote_count=1)
        choice_b = PollChoice.objects.create(poll=poll, text="Choice B", vote_count=0)

        # Student has already voted in this poll
        PollVote.objects.create(poll=poll, choice=choice_a, voter=student)

        client = APIClient()
        client.force_authenticate(user=student)

        # Student attempts to cast another vote
        payload = {"poll": poll.pk, "choice": choice_b.pk}
        resp = client.post(f"/api/gymkhana/polls/{poll.pk}/vote/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data

        # Tally remains unchanged; no duplicate vote recorded
        choice_b.refresh_from_db()
        assert choice_b.vote_count == 0
        choice_a.refresh_from_db()
        assert choice_a.vote_count == 1
        assert PollVote.objects.filter(poll=poll, voter=student).count() == 1


# ---------------------------------------------------------------------------
# TC-UC-21 to TC-UC-22: UC-GYM-008 Club Leadership Replacement
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestClubLeadershipReplacement:
    def test_tc_uc_21_replace_club_leadership_main_flow(self):
        """TC-UC-21 (source_id: UC-GYM-008 Main Flow):
        Verify main success scenario for replacing club coordinator and co-coordinator by Club Head.
        """
        student_01 = _make_user("student_01_uc21")
        student_02 = _make_user("student_02_uc21")
        student_03 = _make_user("student_03_uc21")
        student_04 = _make_user("student_04_uc21")
        faculty_01 = _make_user("faculty_01_uc21")

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
        assert club.is_head(student_03) is True
        assert club.is_head(student_04) is True
        assert club.is_head(student_01) is False
        assert club.is_head(student_02) is False

    def test_tc_uc_22_replace_leadership_invalid_leader_exception_flow(self):
        """TC-UC-22 (source_id: UC-GYM-008 Exception Flow):
        Verify exception flow when proposed leader is invalid or actor is unauthorized,
        current leadership remains unchanged.
        """
        student_01 = _make_user("student_01_uc22")
        student_02 = _make_user("student_02_uc22")
        faculty_01 = _make_user("faculty_01_uc22")

        club = _make_club(student_01, student_02, faculty_01, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=student_01)

        invalid_leader_id = 999999
        payload = {
            "coordinator": invalid_leader_id,
        }
        resp = client.patch(f"/api/gymkhana/clubs/{club.pk}/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data

        club.refresh_from_db()
        assert club.coordinator == student_01
        assert club.co_coordinator == student_02


# ---------------------------------------------------------------------------
# TC-UC-23 to TC-UC-24: UC-GYM-009 Club Budget Request
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestClubBudgetRequests:
    def test_tc_uc_23_submit_budget_request_main_flow(self):
        """TC-UC-23 (source_id: UC-GYM-009 Main Flow):
        Verify main success scenario for submitting and retaining a club budget request for tracking.
        """
        coordinator = _make_user("coord_uc23")
        co_coordinator = _make_user("cocoord_uc23")
        faculty = _make_user("faculty_uc23")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        quote_file = SimpleUploadedFile("quote.pdf", b"fake pdf quote", content_type="application/pdf")
        payload = {
            "club": club.pk,
            "purpose": "Equipment purchase",
            "amount": "15000.00",
            "supporting_file": quote_file,
            "description": "New badminton rackets",
        }
        resp = client.post("/api/gymkhana/budget-requests/", payload, format="multipart")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["status"] == "open"
        assert resp.data["purpose"] == "Equipment purchase"
        assert resp.data["amount"] == "15000.00"

        req = ClubBudgetRequest.objects.get(pk=resp.data["id"])
        assert req.status == "open"
        assert req.amount == Decimal("15000.00")
        assert req.requested_by == coordinator

    def test_tc_uc_24_submit_budget_request_negative_or_missing_file_exception_flow(self):
        """TC-UC-24 (source_id: UC-GYM-009 Exception Flow):
        Verify exception flow when amount is negative or required file is missing,
        request is rejected and not stored.
        """
        coordinator = _make_user("coord_uc24")
        co_coordinator = _make_user("cocoord_uc24")
        faculty = _make_user("faculty_uc24")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        # Case 1: Negative amount
        quote_file = SimpleUploadedFile("quote.pdf", b"fake quote", content_type="application/pdf")
        payload_negative = {
            "club": club.pk,
            "purpose": "Negative budget",
            "amount": "-500.00",
            "supporting_file": quote_file,
            "description": "Negative amount",
        }
        resp_neg = client.post("/api/gymkhana/budget-requests/", payload_negative, format="multipart")
        assert resp_neg.status_code == status.HTTP_400_BAD_REQUEST, resp_neg.data
        assert not ClubBudgetRequest.objects.filter(purpose="Negative budget").exists()

        # Case 2: Missing supporting file
        payload_no_file = {
            "club": club.pk,
            "purpose": "Missing file budget",
            "amount": "500.00",
            "description": "Missing file",
        }
        resp_nofile = client.post("/api/gymkhana/budget-requests/", payload_no_file, format="multipart")
        assert resp_nofile.status_code == status.HTTP_400_BAD_REQUEST, resp_nofile.data
        assert not ClubBudgetRequest.objects.filter(purpose="Missing file budget").exists()


# ---------------------------------------------------------------------------
# TC-UC-25 to TC-UC-26: UC-GYM-010 Club Event Report
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestClubEventReports:
    def test_tc_uc_25_submit_event_report_main_flow(self):
        """TC-UC-25 (source_id: UC-GYM-010 Main Flow):
        Verify main success scenario for submitting documented club event report by Club Head.
        """
        coordinator = _make_user("coord_uc25")
        co_coordinator = _make_user("cocoord_uc25")
        faculty = _make_user("faculty_uc25")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")
        student_01 = _make_user("student_01_uc25")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        report_file = SimpleUploadedFile(
            "event_summary.pdf", b"fake event summary pdf", content_type="application/pdf"
        )
        payload = {
            "club": club.pk,
            "student_incharge": student_01.pk,
            "event_name": "Coding Contest",
            "event_date": "2026-11-10",
            "description": "Over 50 participants",
            "report_file": report_file,
        }
        resp = client.post("/api/gymkhana/event-reports/", payload, format="multipart")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["event_name"] == "Coding Contest"

        report = ClubEventReport.objects.get(pk=resp.data["id"])
        assert report.club == club
        assert report.student_incharge == student_01
        assert report.event_name == "Coding Contest"
        assert report.event_date == datetime.date(2026, 11, 10)
        assert report.submitted_by == coordinator

    def test_tc_uc_26_submit_event_report_missing_file_exception_flow(self):
        """TC-UC-26 (source_id: UC-GYM-010 Exception Flow):
        Verify exception flow when required report file or required references are missing/invalid,
        report is not accepted.
        """
        coordinator = _make_user("coord_uc26")
        co_coordinator = _make_user("cocoord_uc26")
        faculty = _make_user("faculty_uc26")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")
        student_01 = _make_user("student_01_uc26")

        client = APIClient()
        client.force_authenticate(user=coordinator)

        # Missing report_file
        payload = {
            "club": club.pk,
            "student_incharge": student_01.pk,
            "event_name": "Coding Contest Incomplete",
            "event_date": "2026-11-10",
            "description": "Missing report file",
        }
        resp = client.post("/api/gymkhana/event-reports/", payload, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert not ClubEventReport.objects.filter(event_name="Coding Contest Incomplete").exists()


# ---------------------------------------------------------------------------
# TC-UC-27 to TC-UC-28: UC-GYM-011 Club Approval
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestClubApproval:
    def test_tc_uc_27_approve_open_club_main_flow(self):
        """TC-UC-27 (source_id: UC-GYM-011 Main Flow):
        Verify main success scenario for approving an open club by Student Admin.
        """
        student_admin = _make_user("admin_uc27", is_staff=True)
        coordinator = _make_user("coord_uc27")
        co_coordinator = _make_user("cocoord_uc27")
        faculty = _make_user("faculty_uc27")

        club = _make_club(coordinator, co_coordinator, faculty, status="open")

        client = APIClient()
        client.force_authenticate(user=student_admin)

        resp = client.post(f"/api/gymkhana/clubs/{club.pk}/approve/", format="json")
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["status"] == "confirmed"

        club.refresh_from_db()
        assert club.status == "confirmed"

    def test_tc_uc_28_approve_already_confirmed_club_exception_flow(self):
        """TC-UC-28 (source_id: UC-GYM-011 Exception Flow):
        Verify exception flow when club is not open or cannot be updated, no approval transition occurs.
        """
        student_admin = _make_user("admin_uc28", is_staff=True)
        coordinator = _make_user("coord_uc28")
        co_coordinator = _make_user("cocoord_uc28")
        faculty = _make_user("faculty_uc28")

        # Club already has status 'confirmed' (not open)
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=student_admin)

        resp = client.post(f"/api/gymkhana/clubs/{club.pk}/approve/", format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data

        club.refresh_from_db()
        assert club.status == "confirmed"


# ---------------------------------------------------------------------------
# TC-UC-29 to TC-UC-30: UC-GYM-012 Faculty Review of Event Reports
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFacultyReviewEventReports:
    def test_tc_uc_29_faculty_councillor_reviews_reports_main_flow(self):
        """TC-UC-29 (source_id: UC-GYM-012 Main Flow):
        Verify main success scenario where assigned Club Faculty Councillor accesses
        and reviews submitted reports for assigned club.
        """
        coordinator = _make_user("coord_uc29")
        co_coordinator = _make_user("cocoord_uc29")
        faculty_a = _make_user("faculty_a_uc29")
        student_01 = _make_user("student_01_uc29")
        club_a = _make_club(coordinator, co_coordinator, faculty_a, status="confirmed", name="Club Review A")

        report_file = SimpleUploadedFile("summary.pdf", b"PDF bytes", content_type="application/pdf")
        report = ClubEventReport.objects.create(
            club=club_a,
            submitted_by=coordinator,
            student_incharge=student_01,
            event_name="Robotics Expo",
            description="Details of robotics expo",
            event_date=datetime.date(2026, 11, 10),
            report_file=report_file,
        )

        client = APIClient()
        client.force_authenticate(user=faculty_a)

        resp = client.get(f"/api/gymkhana/event-reports/{report.pk}/")
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["id"] == report.pk
        assert resp.data["event_name"] == "Robotics Expo"
        assert resp.data["description"] == "Details of robotics expo"
        assert "summary" in resp.data["report_file"]

    def test_tc_uc_30_unassigned_faculty_access_denied_exception_flow(self):
        """TC-UC-30 (source_id: UC-GYM-012 Exception Flow):
        Verify exception flow when faculty user is not assigned to the club,
        system denies access to club's reports.
        """
        coordinator = _make_user("coord_uc30")
        co_coordinator = _make_user("cocoord_uc30")
        faculty_a = _make_user("faculty_a_uc30")
        faculty_other = _make_user("faculty_other_uc30")
        student_01 = _make_user("student_01_uc30")
        club_a = _make_club(coordinator, co_coordinator, faculty_a, status="confirmed", name="Club Review B")

        report_file = SimpleUploadedFile("summary.pdf", b"PDF bytes", content_type="application/pdf")
        report = ClubEventReport.objects.create(
            club=club_a,
            submitted_by=coordinator,
            student_incharge=student_01,
            event_name="Sports Meet",
            description="Details of sports meet",
            event_date=datetime.date(2026, 11, 10),
            report_file=report_file,
        )

        client = APIClient()
        client.force_authenticate(user=faculty_other)

        resp = client.get(f"/api/gymkhana/event-reports/{report.pk}/")
        assert resp.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ], resp.data
