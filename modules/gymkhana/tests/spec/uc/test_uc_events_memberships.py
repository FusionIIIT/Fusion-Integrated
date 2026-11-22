# ruff: noqa: N802
from datetime import date

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.gymkhana.models.club import Club, ClubLeadership
from modules.gymkhana.models.membership import ClubMembership

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
    stub_iam(make_session(user_id=user_id, kind=kind, modules=("gymkhana",), permissions=tuple(permissions)))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock_token")
    return client


def test_TC_GYM_011_UC_GYM_003_Main_Success_Flow(stub_iam, confirmed_club):
    """TC-GYM-011; source_id: UC-GYM-003 Main Success Flow"""
    client = client_for(stub_iam, 101, ("gymkhana.event.book",))
    response = client.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/events/",
        {"title": "Literature Fest", "venue": "Auditorium", "date": str(date.today()), "start_time": "10:00:00", "end_time": "12:00:00", "description": "Annual fest"},
        format="json",
    )
    assert response.status_code == 201
    assert confirmed_club.bookings.filter(booking_type="event").count() == 1


def test_TC_GYM_012_UC_GYM_003_Alternative_A1(stub_iam, confirmed_club):
    """TC-GYM-012; source_id: UC-GYM-003 Alternative A1"""
    client = client_for(stub_iam, 101, ("gymkhana.session.book", "gymkhana.event.book"))
    session = client.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/sessions/",
        {"title": "Session", "venue": "CC1", "date": str(date.today()), "start_time": "10:00:00", "end_time": "12:00:00"},
        format="json",
    )
    assert session.status_code == 201
    before = confirmed_club.bookings.count()
    response = client.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/events/",
        {"title": "Overlap Event", "venue": "CC1", "date": str(date.today()), "start_time": "11:00:00", "end_time": "13:00:00"},
        format="json",
    )
    assert response.status_code == 409
    assert confirmed_club.bookings.count() == before


def test_TC_GYM_013_UC_GYM_003_Exception_E1_Invalid_Venue(stub_iam, confirmed_club):
    """TC-GYM-013; source_id: UC-GYM-003 Exception E1 Invalid Venue"""
    client = client_for(stub_iam, 101, ("gymkhana.event.book",))
    response = client.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/events/",
        {"title": "Invalid", "venue": "NOT-CONFIGURED", "date": str(date.today()), "start_time": "10:00:00", "end_time": "12:00:00"},
        format="json",
    )
    assert response.status_code in (400, 422)
    assert not confirmed_club.bookings.exists()


def test_TC_GYM_014_UC_GYM_003_Exception_E1_Invalid_Faculty_Reference(stub_iam, confirmed_club):
    """TC-GYM-014; source_id: UC-GYM-003 Exception E1 Invalid Faculty Reference"""
    confirmed_club.faculty_councillor_id = 999
    confirmed_club.save(update_fields=["faculty_councillor_id"])
    client = client_for(stub_iam, 101, ("gymkhana.event.book",))
    response = client.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/events/",
        {"title": "Invalid Faculty", "venue": "Auditorium", "date": str(date.today()), "start_time": "10:00:00", "end_time": "12:00:00"},
        format="json",
    )
    assert response.status_code in (400, 422)
    assert not confirmed_club.bookings.exists()


def test_TC_GYM_015_UC_GYM_003_Exception_E1_Invalid_Time_Range(stub_iam, confirmed_club):
    """TC-GYM-015; source_id: UC-GYM-003 Exception E1 Invalid Time Range"""
    client = client_for(stub_iam, 101, ("gymkhana.event.book",))
    response = client.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/events/",
        {"title": "Invalid", "venue": "Auditorium", "date": str(date.today()), "start_time": "12:00:00", "end_time": "10:00:00"},
        format="json",
    )
    assert response.status_code in (400, 422)
    assert not confirmed_club.bookings.exists()


def test_TC_GYM_016_UC_GYM_003_Exception_E1_Storage_Failure(stub_iam, confirmed_club):
    """TC-GYM-016; source_id: UC-GYM-003 Exception E1 Storage Failure"""
    pytest.skip("NOT_AUTOMATED: event storage failure has no injectable storage interface")


def test_TC_GYM_017_UC_GYM_004_Main_Success_Flow(stub_iam, confirmed_club):
    """TC-GYM-017; source_id: UC-GYM-004 Main Success Flow"""
    client = client_for(stub_iam, 103, ("gymkhana.membership.apply",))
    response = client.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/memberships/apply/",
        {"remarks": "Eager member"},
        format="json",
    )
    assert response.status_code == 201
    membership = ClubMembership.objects.get(club=confirmed_club, student_id=103)
    assert membership.status == "open"


def test_TC_GYM_018_UC_GYM_004_Alternative_A1(stub_iam, confirmed_club):
    """TC-GYM-018; source_id: UC-GYM-004 Alternative A1"""
    other = Club.objects.create(name="Music Club", category="Cultural", faculty_councillor_id=201, status="confirmed")
    client = client_for(stub_iam, 103, ("gymkhana.membership.apply",))
    first = client.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/memberships/apply/",
        {"remarks": "Literature"},
        format="json",
    )
    second = client.post(
        f"/api/v1/gymkhana/clubs/{other.id}/memberships/apply/",
        {"remarks": "Music"},
        format="json",
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert ClubMembership.objects.filter(student_id=103).count() == 2


def test_TC_GYM_019_UC_GYM_004_Exception_E1(stub_iam, confirmed_club):
    """TC-GYM-019; source_id: UC-GYM-004 Exception E1"""
    client = client_for(stub_iam, 103, ("gymkhana.membership.apply",))
    first = client.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/memberships/apply/",
        {"remarks": "First"},
        format="json",
    )
    assert first.status_code == 201
    before = ClubMembership.objects.filter(club=confirmed_club, student_id=103).count()
    duplicate = client.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/memberships/apply/",
        {"remarks": "Duplicate"},
        format="json",
    )
    assert duplicate.status_code == 409
    assert ClubMembership.objects.filter(club=confirmed_club, student_id=103).count() == before


def test_TC_GYM_020_BR_GYM_007_Confirmed_Club_Requirement(stub_iam, confirmed_club, gymkhana_users):
    """TC-GYM-020; source_id: BR-GYM-007 Confirmed Club Requirement"""
    confirmed_club.status = "open"
    confirmed_club.save(update_fields=["status"])
    client = client_for(stub_iam, 103, ("gymkhana.membership.apply",))
    response = client.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/memberships/apply/",
        {"remarks": "No"},
        format="json",
    )
    assert response.status_code in (400, 409)
    assert not ClubMembership.objects.filter(club=confirmed_club, student_id=103).exists()


def test_TC_GYM_021_UC_GYM_005_Main_Success_Flow(stub_iam, confirmed_club):
    """TC-GYM-021; source_id: UC-GYM-005 Main Success Flow"""
    student = client_for(stub_iam, 103, ("gymkhana.membership.apply",))
    applied = student.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/memberships/apply/",
        {"remarks": ""},
        format="json",
    )
    assert applied.status_code == 201
    membership_id = applied.json()["id"]
    leader = client_for(stub_iam, 101, ("gymkhana.membership.approve",))
    response = leader.post(
        f"/api/v1/gymkhana/memberships/{membership_id}/approve/",
        {"remarks": "Welcome"},
        format="json",
    )
    assert response.status_code == 200
    membership = ClubMembership.objects.get(id=membership_id)
    assert membership.status == "confirmed"
    assert membership.remarks == "Welcome"


def test_TC_GYM_022_UC_GYM_005_Alternative_A1(stub_iam, confirmed_club):
    """TC-GYM-022; source_id: UC-GYM-005 Alternative A1"""
    for remark in ("One", "Two"):
        ClubMembership.objects.create(club=confirmed_club, student_id=104 if remark == "One" else 105, status="open", remarks=remark)
    leader = client_for(stub_iam, 101, ("gymkhana.membership.approve",))
    selected = list(ClubMembership.objects.filter(club=confirmed_club))
    for membership in selected:
        response = leader.post(
            f"/api/v1/gymkhana/memberships/{membership.id}/approve/",
            {"remarks": "Approved"},
            format="json",
        )
        assert response.status_code == 200
        membership.refresh_from_db()
        assert membership.status == "confirmed"
