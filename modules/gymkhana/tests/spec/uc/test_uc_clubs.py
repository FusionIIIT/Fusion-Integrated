# ruff: noqa: N802
from datetime import date

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.gymkhana.models.club import Club, ClubLeadership
from modules.gymkhana.models.notification import GymkhanaNotificationOutbox

pytestmark = pytest.mark.django_db


@pytest.fixture
def gymkhana_users():
    for user_id, kind in ((101, "student"), (102, "student"), (103, "student"), (201, "faculty")):
        UserRef.objects.create(
            user_id=user_id,
            username=f"u{user_id}",
            display_name=f"User {user_id}",
            kind=kind,
            discipline="CSE" if kind == "student" else "",
            batch_year=2023 if kind == "student" else None,
        )
    return 101, 102, 103, 201


@pytest.fixture
def confirmed_club(gymkhana_users):
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


def client_for(stub_iam, user_id, permissions=(), kind="student"):
    stub_iam(
        make_session(
            user_id=user_id,
            kind=kind,
            modules=("gymkhana",),
            permissions=tuple(permissions),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock_token")
    return client


def test_TC_GYM_001_UC_GYM_001_Main_Success_Flow(stub_iam, gymkhana_users):
    """TC-GYM-001; source_id: UC-GYM-001 Main Success Flow"""
    client = client_for(
        stub_iam,
        201,
        ("gymkhana.club.create",),
        "faculty",
    )
    response = client.post(
        "/api/v1/gymkhana/clubs/",
        {
            "name": "Robotics Club",
            "category": "Technical",
            "description": "Build robots",
            "coordinator_id": 101,
            "co_coordinator_id": 102,
            "faculty_councillor_id": 201,
        },
        format="json",
    )
    assert response.status_code == 201
    club = Club.objects.get(name="Robotics Club")
    assert club.status == "open"
    assert ClubLeadership.objects.filter(club=club, is_current=True).count() == 2


def test_TC_GYM_002_UC_GYM_001_Alternative_A1(stub_iam, gymkhana_users):
    """TC-GYM-002; source_id: UC-GYM-001 Alternative A1"""
    client = client_for(stub_iam, 201, ("gymkhana.club.create",), "faculty")
    response = client.post(
        "/api/v1/gymkhana/clubs/",
        {
            "name": "Invalid Leader Club",
            "category": "Sports",
            "description": "Test",
            "coordinator_id": 999,
            "co_coordinator_id": 102,
            "faculty_councillor_id": 201,
        },
        format="json",
    )
    assert response.status_code in (400, 422)
    assert not Club.objects.filter(name="Invalid Leader Club").exists()


def test_TC_GYM_003_BR_GYM_003_Category_Constraint(stub_iam, gymkhana_users):
    """TC-GYM-003; source_id: BR-GYM-003 Category Constraint"""
    client = client_for(stub_iam, 201, ("gymkhana.club.create",), "faculty")
    response = client.post(
        "/api/v1/gymkhana/clubs/",
        {
            "name": "Disallowed Category Club",
            "category": "Other",
            "description": "Test",
            "coordinator_id": 101,
            "co_coordinator_id": 102,
            "faculty_councillor_id": 201,
        },
        format="json",
    )
    assert response.status_code in (400, 422)
    assert not Club.objects.filter(name="Disallowed Category Club").exists()


def test_TC_GYM_004_UC_GYM_001_Exception_E1(gymkhana_users):
    """TC-GYM-004; source_id: UC-GYM-001 Exception E1"""
    pytest.skip("NOT_AUTOMATED: no club data storage failure interface is exposed")


def test_TC_GYM_005_UC_GYM_002_Main_Success_Flow(stub_iam, confirmed_club):
    """TC-GYM-005; source_id: UC-GYM-002 Main Success Flow"""
    client = client_for(stub_iam, 101, ("gymkhana.session.book", "gymkhana.club.view"))
    response = client.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/sessions/",
        {
            "title": "Weekly Practice",
            "venue": "CC1",
            "date": str(date.today()),
            "start_time": "16:00:00",
            "end_time": "18:00:00",
            "description": "Practice",
        },
        format="json",
    )
    assert response.status_code == 201
    assert confirmed_club.bookings.filter(booking_type="session").count() == 1
    assert GymkhanaNotificationOutbox.objects.count() >= 1


def test_TC_GYM_006_UC_GYM_002_Alternative_A1(stub_iam, confirmed_club):
    """TC-GYM-006; source_id: UC-GYM-002 Alternative A1"""
    client = client_for(stub_iam, 101, ("gymkhana.session.book",))
    first = client.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/sessions/",
        {"title": "First", "venue": "CC1", "date": str(date.today()), "start_time": "16:00:00", "end_time": "18:00:00"},
        format="json",
    )
    assert first.status_code == 201
    before = confirmed_club.bookings.count()
    response = client.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/sessions/",
        {"title": "Overlap", "venue": "CC1", "date": str(date.today()), "start_time": "17:00:00", "end_time": "19:00:00"},
        format="json",
    )
    assert response.status_code == 409
    assert confirmed_club.bookings.count() == before


def test_TC_GYM_007_UC_GYM_002_Exception_E1_Invalid_Venue(stub_iam, confirmed_club):
    """TC-GYM-007; source_id: UC-GYM-002 Exception E1 Invalid Venue"""
    client = client_for(stub_iam, 101, ("gymkhana.session.book",))
    response = client.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/sessions/",
        {"title": "Invalid", "venue": "NOT-CONFIGURED", "date": str(date.today()), "start_time": "16:00:00", "end_time": "17:00:00"},
        format="json",
    )
    assert response.status_code in (400, 422)
    assert not confirmed_club.bookings.exists()


def test_TC_GYM_008_UC_GYM_002_Exception_E1_Invalid_Time_Range(stub_iam, confirmed_club):
    """TC-GYM-008; source_id: UC-GYM-002 Exception E1 Invalid Time Range"""
    client = client_for(stub_iam, 101, ("gymkhana.session.book",))
    response = client.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/sessions/",
        {"title": "Invalid", "venue": "CC1", "date": str(date.today()), "start_time": "18:00:00", "end_time": "17:00:00"},
        format="json",
    )
    assert response.status_code in (400, 422)
    assert not confirmed_club.bookings.exists()


def test_TC_GYM_009_UC_GYM_002_Exception_E1_Storage_Failure(monkeypatch, stub_iam, confirmed_club):
    """TC-GYM-009; source_id: UC-GYM-002 Exception E1 Storage Failure"""
    pytest.skip("NOT_AUTOMATED: session booking storage failure has no injectable storage interface")


def test_TC_GYM_010_UC_GYM_002_Exception_E1_Notification_Failure(stub_iam, confirmed_club):
    """TC-GYM-010; source_id: UC-GYM-002 Exception E1 Notification Failure"""
    pytest.skip("NOT_AUTOMATED: notification processing failure cannot be induced through the available interfaces")

