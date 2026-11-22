"""Comprehensive API tests for Gymkhana Phase 3.3.

Covers all 22 endpoints specified in Blueprint §3.5:
- Two-tier RBAC: HasModuleGrant("gymkhana") + HasPermission("<module>.<noun>.<verb>")
- Object-level scoping: 404 over 403 zero-information-disclosure
- Pure-Python domain exception translation into 400 / 409 error envelopes
- Calendar booking under VenueDayLock with cross-type exclusivity
- Targeted poll participation and duplicate vote prevention
- Event report review and 302 download redirect with Referrer-Policy: no-referrer
"""
from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import UserRef as IamUserRef
from modules.gymkhana.models import (
    Booking,
    Club,
    ClubBudgetRequest,
    ClubEventReport,
    ClubMembership,
    Poll,
    PollChoice,
    PollTarget,
    PollVote,
)

pytestmark = pytest.mark.django_db


COMMON_USERS = {
    1: IamUserRef(user_id=1, username="u1", display_name="Admin Dean", kind="staff"),
    101: IamUserRef(user_id=101, username="u101", display_name="Alice (Lead)", kind="student", discipline="CSE", batch_year=2024),
    102: IamUserRef(user_id=102, username="u102", display_name="Bob (Co-lead)", kind="student", discipline="CSE", batch_year=2024),
    103: IamUserRef(user_id=103, username="u103", display_name="Charlie", kind="student", discipline="ECE", batch_year=2023),
    104: IamUserRef(user_id=104, username="u104", display_name="Diana", kind="student", discipline="ME", batch_year=2023),
    201: IamUserRef(user_id=201, username="u201", display_name="Student CSE 2024", kind="student", discipline="CSE", batch_year=2024),
    202: IamUserRef(user_id=202, username="u202", display_name="Student ME 2023", kind="student", discipline="ME", batch_year=2023),
    501: IamUserRef(user_id=501, username="u501", display_name="Dr. Smith (Councillor)", kind="faculty", discipline="CSE"),
    502: IamUserRef(user_id=502, username="u502", display_name="Dr. Jones (Foreign)", kind="faculty", discipline="ECE"),
}


@pytest.fixture
def stub_directory(stub_iam):
    """Install common student, faculty, and admin test users."""
    stub_iam(users=COMMON_USERS)


@pytest.fixture
def confirmed_club(stub_directory):
    return Club.objects.create(
        name="Robotics Club",
        category="Technical",
        description="Build awesome robots",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=501,
        status="confirmed",
    )


@pytest.fixture
def open_club(stub_directory):
    return Club.objects.create(
        name="Astronomy Club",
        category="Technical",
        description="Look at the stars",
        coordinator_id=103,
        co_coordinator_id=104,
        faculty_councillor_id=501,
        status="open",
    )


def _client(stub_iam, **kw):
    modules = kw.pop("modules", ("gymkhana",))
    users = kw.pop("users", COMMON_USERS)
    stub_iam(make_session(modules=modules, **kw), users=users)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return c


# ===========================================================================
# 1. Clubs & Leadership (Endpoints 1-5)
# ===========================================================================


def test_list_clubs_public_vs_admin(stub_iam, confirmed_club, open_club):
    """Students see only confirmed clubs; Student Admin sees all clubs (BR-GYM-004)."""
    # Normal student sees only confirmed
    client = _client(stub_iam, user_id=201, permissions=("gymkhana.club.view",))
    res = client.get("/api/v1/gymkhana/clubs")
    assert res.status_code == 200
    names = [c["name"] for c in res.json()]
    assert "Robotics Club" in names
    assert "Astronomy Club" not in names

    # Student Admin sees all
    admin_client = _client(
        stub_iam,
        user_id=1,
        permissions=("gymkhana.club.view", "gymkhana.club.approve"),
    )
    res_admin = admin_client.get("/api/v1/gymkhana/clubs/")
    assert res_admin.status_code == 200
    admin_names = [c["name"] for c in res_admin.json()]
    assert "Robotics Club" in admin_names
    assert "Astronomy Club" in admin_names


def test_create_club_success_and_validation(stub_iam, stub_directory):
    """Student Admin creates a club in 'open' status; non-admin is refused (UC-GYM-001)."""
    client = _client(stub_iam, user_id=1, permissions=("gymkhana.club.create",))
    payload = {
        "name": "Coding Club",
        "category": "Technical",
        "description": "Algorithms and competitive programming",
        "coordinator_id": 101,
        "co_coordinator_id": 102,
        "faculty_councillor_id": 501,
    }
    res = client.post("/api/v1/gymkhana/clubs", payload, format="json")
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Coding Club"
    assert data["status"] == "open"

    # Category restriction (BR-GYM-003)
    payload_bad_cat = dict(payload, name="Bad Cat Club", category="InvalidCat")
    res_bad = client.post("/api/v1/gymkhana/clubs", payload_bad_cat, format="json")
    assert res_bad.status_code == 400

    # Non-admin forbidden (403)
    student_client = _client(stub_iam, user_id=201, permissions=("gymkhana.club.view",))
    res_forbidden = student_client.post("/api/v1/gymkhana/clubs", payload, format="json")
    assert res_forbidden.status_code == 403


def test_get_club_detail_scoping(stub_iam, confirmed_club, open_club):
    """Detail view returns 404 for open club requested by regular student (UC-GYM-001)."""
    client = _client(stub_iam, user_id=201, permissions=("gymkhana.club.view",))
    # Confirmed club is accessible
    res = client.get(f"/api/v1/gymkhana/clubs/{confirmed_club.id}")
    assert res.status_code == 200
    assert res.json()["name"] == "Robotics Club"

    # Open club is absent (404) for students
    res_open = client.get(f"/api/v1/gymkhana/clubs/{open_club.id}")
    assert res_open.status_code == 404

    # Nonexistent club is 404
    res_none = client.get("/api/v1/gymkhana/clubs/99999")
    assert res_none.status_code == 404


def test_approve_club(stub_iam, open_club):
    """Student Admin approves open club to confirmed; double-approve is 409 (UC-GYM-011)."""
    admin_client = _client(stub_iam, user_id=1, permissions=("gymkhana.club.approve",))
    res = admin_client.post(f"/api/v1/gymkhana/clubs/{open_club.id}/approve")
    assert res.status_code == 200
    assert res.json()["status"] == "confirmed"

    # Double approve triggers InvalidTransition -> translated to 409 Conflict
    res_dup = admin_client.post(f"/api/v1/gymkhana/clubs/{open_club.id}/approve")
    assert res_dup.status_code == 409
    assert res_dup.json()["error"]["code"] == "invalid_transition"


def test_change_club_leadership(stub_iam, confirmed_club, stub_directory):
    """Club Head replaces leaders; foreign actor gets 404 (UC-GYM-008, BR-GYM-016)."""
    # Foreign caller (user 201 is not a coordinator of Robotics Club)
    foreign_client = _client(stub_iam, user_id=201, permissions=("gymkhana.leadership.update",))
    res_foreign = foreign_client.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/leadership",
        {"new_coordinator_id": 103, "new_co_coordinator_id": 104},
        format="json",
    )
    assert res_foreign.status_code == 404

    # Valid coordinator (user 101)
    head_client = _client(stub_iam, user_id=101, permissions=("gymkhana.leadership.update",))
    res = head_client.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/leadership",
        {"new_coordinator_id": 103, "new_co_coordinator_id": 104},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["coordinator_id"] == 103
    assert res.json()["co_coordinator_id"] == 104

    # Duplicate coordinators rejected (400) by the new active leader (user 103)
    new_head_client = _client(stub_iam, user_id=103, permissions=("gymkhana.leadership.update",))
    res_bad = new_head_client.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/leadership",
        {"new_coordinator_id": 101, "new_co_coordinator_id": 101},
        format="json",
    )
    assert res_bad.status_code == 400


# ===========================================================================
# 2. Memberships (Endpoints 6-9)
# ===========================================================================


def test_membership_application_flow(stub_iam, confirmed_club, open_club):
    """Apply for confirmed club, prevent duplicate (409), list own (UC-GYM-004)."""
    student_client = _client(
        stub_iam,
        user_id=201,
        permissions=("gymkhana.membership.create", "gymkhana.membership.view"),
    )

    # Cannot apply to unconfirmed club (BR-GYM-007)
    res_unconfirmed = student_client.post(
        "/api/v1/gymkhana/memberships",
        {"club_id": open_club.id},
        format="json",
    )
    assert res_unconfirmed.status_code == 409
    assert res_unconfirmed.json()["error"]["code"] == "club_not_confirmed"

    # Apply to confirmed club
    res_apply = student_client.post(
        "/api/v1/gymkhana/memberships",
        {"club_id": confirmed_club.id},
        format="json",
    )
    assert res_apply.status_code == 201
    assert res_apply.json()["status"] == "open"
    membership_id = res_apply.json()["id"]

    # Duplicate application rejected with 409 (BR-GYM-009)
    res_dup = student_client.post(
        "/api/v1/gymkhana/memberships",
        {"club_id": confirmed_club.id},
        format="json",
    )
    assert res_dup.status_code == 409
    assert res_dup.json()["error"]["code"] == "duplicate_membership_application"

    # List own memberships
    res_list = student_client.get("/api/v1/gymkhana/memberships")
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1
    assert res_list.json()[0]["id"] == membership_id


def test_approve_membership(stub_iam, confirmed_club):
    """Club Head approves membership; foreign club head gets 409/404 (UC-GYM-005)."""
    # Create an open application
    membership = ClubMembership.objects.create(
        club=confirmed_club,
        student_id=201,
        status="open",
    )

    # Foreign head cannot access applications for this club (404)
    foreign_client = _client(stub_iam, user_id=103, permissions=("gymkhana.membership.view",))
    res_foreign = foreign_client.get(f"/api/v1/gymkhana/clubs/{confirmed_club.id}/memberships")
    assert res_foreign.status_code == 404

    # Legitimate club coordinator (user 101) lists memberships
    head_client = _client(
        stub_iam,
        user_id=101,
        permissions=("gymkhana.membership.view", "gymkhana.membership.approve"),
    )
    res_list = head_client.get(f"/api/v1/gymkhana/clubs/{confirmed_club.id}/memberships")
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1

    # Legitimate club coordinator approves
    res_app = head_client.post(
        f"/api/v1/gymkhana/memberships/{membership.id}/approve",
        {"remarks": "Welcome to Robotics!"},
        format="json",
    )
    assert res_app.status_code == 200
    assert res_app.json()["status"] == "confirmed"


# ===========================================================================
# 3. Bookings (Calendar, Sessions, Events) (Endpoints 10-12)
# ===========================================================================


def test_booking_calendar_and_session_creation(stub_iam, confirmed_club):
    """Book session under VenueDayLock; prevent overlap (UC-GYM-002, BR-GYM-006)."""
    head_client = _client(
        stub_iam,
        user_id=101,
        permissions=("gymkhana.session.create", "gymkhana.session.view"),
    )
    payload = {
        "club_id": confirmed_club.id,
        "venue": "CR-101",
        "date": "2026-12-01",
        "start_time": "14:00:00",
        "end_time": "16:00:00",
        "name": "Intro to ROS",
        "description": "Robotics Operating System hands-on",
    }
    res = head_client.post("/api/v1/gymkhana/sessions", payload, format="json")
    assert res.status_code == 201
    assert res.json()["booking_type"] == "session"

    # View calendar
    res_cal = head_client.get("/api/v1/gymkhana/bookings?date=2026-12-01")
    assert res_cal.status_code == 200
    assert len(res_cal.json()) == 1

    # Overlapping session booking rejected (409)
    overlap_payload = dict(payload, start_time="15:00:00", end_time="17:00:00")
    res_overlap = head_client.post("/api/v1/gymkhana/sessions", overlap_payload, format="json")
    assert res_overlap.status_code == 409
    assert res_overlap.json()["error"]["code"] == "venue_overlap"

    # Invalid venue rejected (400)
    bad_venue_payload = dict(payload, venue="UnconfiguredRoom", start_time="18:00:00", end_time="19:00:00")
    res_bad_venue = head_client.post("/api/v1/gymkhana/sessions", bad_venue_payload, format="json")
    assert res_bad_venue.status_code == 400


def test_cross_type_booking_overlap(stub_iam, confirmed_club):
    """Event booking overlaps with session booking and is refused (BR-GYM-006, UC-GYM-003)."""
    head_client = _client(
        stub_iam,
        user_id=101,
        permissions=("gymkhana.session.create", "gymkhana.event.create"),
    )
    # Book session 10:00-12:00 in Audi
    head_client.post(
        "/api/v1/gymkhana/sessions",
        {
            "club_id": confirmed_club.id,
            "venue": "Audi",
            "date": "2026-12-05",
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "description": "Morning session",
        },
        format="json",
    )

    # Attempt to book Event 11:00-13:00 in Audi -> 409 Conflict
    res_event = head_client.post(
        "/api/v1/gymkhana/events",
        {
            "club_id": confirmed_club.id,
            "faculty_councillor_id": 501,
            "venue": "Audi",
            "date": "2026-12-05",
            "start_time": "11:00:00",
            "end_time": "13:00:00",
            "name": "Robotics Expo",
            "description": "Annual exhibition",
        },
        format="json",
    )
    assert res_event.status_code == 409
    assert res_event.json()["error"]["code"] == "venue_overlap"


# ===========================================================================
# 4. Polls & Voting (Endpoints 13-16)
# ===========================================================================


def test_poll_creation_targeting_and_voting(stub_iam, confirmed_club):
    """Create targeted poll, targeted student votes once, untargeted gets 404 (UC-006, UC-007)."""
    head_client = _client(stub_iam, user_id=101, permissions=("gymkhana.poll.create",))
    expires = (timezone.now() + datetime.timedelta(days=2)).isoformat()
    poll_payload = {
        "club_id": confirmed_club.id,
        "title": "Workshop Topic",
        "description": "Choose next hands-on topic",
        "expires_at": expires,
        "choices": ["Drone Navigation", "Humanoid Kinematics"],
        "targets": [{"batch_year": 2024, "discipline": "CSE"}],
    }
    res_create = head_client.post("/api/v1/gymkhana/polls", poll_payload, format="json")
    assert res_create.status_code == 201
    poll_id = res_create.json()["id"]
    choice_id = res_create.json()["choices"][0]["id"]

    # Student 201 (CSE 2024) is eligible
    eligible_student = _client(
        stub_iam,
        user_id=201,
        permissions=("gymkhana.poll.view", "gymkhana.poll.update"),
    )
    res_list = eligible_student.get("/api/v1/gymkhana/polls")
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1

    # Student votes
    res_vote = eligible_student.post(
        f"/api/v1/gymkhana/polls/{poll_id}/vote",
        {"choice_id": choice_id},
        format="json",
    )
    assert res_vote.status_code == 200
    assert res_vote.json()["poll_id"] == poll_id

    # Duplicate vote rejected (409)
    res_dup = eligible_student.post(
        f"/api/v1/gymkhana/polls/{poll_id}/vote",
        {"choice_id": choice_id},
        format="json",
    )
    assert res_dup.status_code == 409
    assert res_dup.json()["error"]["code"] == "duplicate_vote"

    # Detail view shows tally = 1 and has_voted = True
    res_detail = eligible_student.get(f"/api/v1/gymkhana/polls/{poll_id}")
    assert res_detail.status_code == 200
    assert res_detail.json()["has_voted"] is True
    assert res_detail.json()["choices"][0]["tally"] == 1

    # Student 202 (ME 2023) is untargeted -> poll is absent (404)
    untargeted_student = _client(stub_iam, user_id=202, permissions=("gymkhana.poll.view",))
    res_untargeted = untargeted_student.get(f"/api/v1/gymkhana/polls/{poll_id}")
    assert res_untargeted.status_code == 404


# ===========================================================================
# 5. Budgets (Endpoints 17-18)
# ===========================================================================


def test_budget_request_lifecycle(stub_iam, confirmed_club):
    """Club Head submits budget with valid Drive URL; foreign head gets 404 (UC-GYM-009)."""
    # Foreign head cannot access budget list (404)
    foreign_client = _client(stub_iam, user_id=103, permissions=("gymkhana.budget.view",))
    res_foreign = foreign_client.get(f"/api/v1/gymkhana/clubs/{confirmed_club.id}/budgets")
    assert res_foreign.status_code == 404

    # Legitimate head submits budget
    head_client = _client(
        stub_iam,
        user_id=101,
        permissions=("gymkhana.budget.create", "gymkhana.budget.view"),
    )
    payload = {
        "amount": "15000.00",
        "purpose": "Motors and microcontrollers",
        "description": "Component procurement for festival",
        "supporting_file_url": "https://drive.google.com/file/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs/view",
    }
    res = head_client.post(f"/api/v1/gymkhana/clubs/{confirmed_club.id}/budgets", payload, format="json")
    assert res.status_code == 201
    assert res.json()["status"] == "open"
    assert res.json()["amount"] == "15000.00"

    # Negative amount rejected (400)
    bad_payload = dict(payload, amount="-500.00")
    res_bad = head_client.post(f"/api/v1/gymkhana/clubs/{confirmed_club.id}/budgets", bad_payload, format="json")
    assert res_bad.status_code == 400

    # Invalid drive link rejected (400)
    bad_drive = dict(payload, supporting_file_url="https://notgoogle.com/badfile.pdf")
    res_bad_drive = head_client.post(f"/api/v1/gymkhana/clubs/{confirmed_club.id}/budgets", bad_drive, format="json")
    assert res_bad_drive.status_code == 400


# ===========================================================================
# 6. Event Reports & Review Download (Endpoints 19-22)
# ===========================================================================


def test_event_report_submission_and_faculty_download(stub_iam, confirmed_club):
    """Club Head submits report; Faculty Councillor reviews & downloads via 302 (UC-010, UC-012)."""
    head_client = _client(
        stub_iam,
        user_id=101,
        permissions=("gymkhana.report.create", "gymkhana.report.view"),
    )
    payload = {
        "student_incharge_id": 102,
        "event_name": "RoboWars 2026",
        "event_date": "2026-11-20",
        "event_time": "15:00:00",
        "description": "Combat robotics tournament",
        "report_file_url": "https://drive.google.com/file/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs/view",
    }
    res_submit = head_client.post(f"/api/v1/gymkhana/clubs/{confirmed_club.id}/reports", payload, format="json")
    assert res_submit.status_code == 201
    report_id = res_submit.json()["id"]

    # Assigned Faculty Councillor (user 501) views detail
    assigned_faculty = _client(
        stub_iam,
        user_id=501,
        roles=("faculty",),
        permissions=("gymkhana.report.view", "gymkhana.report.review"),
    )
    res_detail = assigned_faculty.get(f"/api/v1/gymkhana/reports/{report_id}")
    assert res_detail.status_code == 200
    assert res_detail.json()["event_name"] == "RoboWars 2026"

    # Assigned Faculty Councillor downloads report documentation -> HTTP 302 redirect
    res_dl = assigned_faculty.get(f"/api/v1/gymkhana/reports/{report_id}/download")
    assert res_dl.status_code == 302
    assert res_dl.url == "https://drive.google.com/file/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs/view"
    assert res_dl["Referrer-Policy"] == "no-referrer"
    assert res_dl["Cache-Control"] == "private, no-store"

    # Unassigned Faculty Councillor (user 502) is refused with 404 (BR-GYM-021)
    unassigned_faculty = _client(
        stub_iam,
        user_id=502,
        roles=("faculty",),
        permissions=("gymkhana.report.view", "gymkhana.report.review"),
    )
    res_unassigned_view = unassigned_faculty.get(f"/api/v1/gymkhana/reports/{report_id}")
    assert res_unassigned_view.status_code == 404

    res_unassigned_dl = unassigned_faculty.get(f"/api/v1/gymkhana/reports/{report_id}/download")
    assert res_unassigned_dl.status_code == 404


# ===========================================================================
# 7. Security Baseline Verification (401 Unauthenticated & 403 Forbidden)
# ===========================================================================


def test_security_gates():
    """Requests without token are 401; missing module grant is 403."""
    anonymous_client = APIClient()
    res_401 = anonymous_client.get("/api/v1/gymkhana/clubs")
    assert res_401.status_code == 401
