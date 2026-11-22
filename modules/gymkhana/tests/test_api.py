"""
Integration tests for Gymkhana REST APIs.
"""

from datetime import date, time

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.gymkhana.contracts import (
    get_active_leaderships,
    get_clubs,
    get_memberships,
    get_venue_bookings,
)
from modules.gymkhana.models import (
    Club,
    ClubLeadership,
    ClubMembership,
    VenueBooking,
)

pytestmark = pytest.mark.django_db


def _auth_client(stub_iam, user_id=101, permissions=(), modules=("gymkhana",)):
    stub_iam(make_session(user_id=user_id, modules=modules, permissions=permissions))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return c


def test_club_list_and_create(stub_iam):
    client = _auth_client(
        stub_iam,
        user_id=1,
        permissions=("gymkhana.club.view", "gymkhana.club.admin"),
    )
    # Create club
    resp = client.post(
        "/api/v1/gymkhana/clubs/",
        {
            "name": "Robotics Club",
            "category": "Technical",
            "description": "Robotics development",
            "coordinator_id": 101,
            "co_coordinator_id": 102,
            "faculty_councillor_id": 501,
        },
        format="json",
    )
    assert resp.status_code == 201
    club_id = resp.data["id"]
    assert resp.data["status"] == "open"

    # List clubs
    list_resp = client.get("/api/v1/gymkhana/clubs/")
    assert list_resp.status_code == 200
    assert len(list_resp.data) == 1
    assert list_resp.data[0]["id"] == club_id

    # Confirm club
    conf_resp = client.post(f"/api/v1/gymkhana/clubs/{club_id}/confirm/")
    assert conf_resp.status_code == 200
    assert conf_resp.data["status"] == "confirmed"


def test_venue_booking_api(stub_iam):
    club = Club.objects.create(name="Sports Society", category="Sports", status="confirmed")
    ClubLeadership.objects.create(
        club=club,
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=501,
        is_active=True,
    )
    client = _auth_client(
        stub_iam,
        user_id=101,
        permissions=("gymkhana.club.view", "gymkhana.booking.manage"),
    )

    resp = client.post(
        "/api/v1/gymkhana/bookings/",
        {
            "club": club.id,
            "booking_type": "session",
            "venue_name": "Student Activity Center (SAC)",
            "booking_date": "2026-12-15",
            "start_time": "14:00:00",
            "end_time": "16:00:00",
            "description": "Badminton practice session",
        },
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["venue_name"] == "Student Activity Center (SAC)"

    list_resp = client.get("/api/v1/gymkhana/bookings/")
    assert list_resp.status_code == 200
    assert len(list_resp.data) >= 1


def test_membership_apply_and_approve_api(stub_iam):
    club = Club.objects.create(name="Cultural Club", category="Cultural", status="confirmed")
    ClubLeadership.objects.create(
        club=club,
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=501,
        is_active=True,
    )

    # Student applies
    student_client = _auth_client(
        stub_iam,
        user_id=201,
        permissions=("gymkhana.club.view", "gymkhana.membership.apply"),
    )
    apply_resp = student_client.post(f"/api/v1/gymkhana/clubs/{club.id}/apply/")
    assert apply_resp.status_code == 201
    mem_id = apply_resp.data["id"]
    assert apply_resp.data["status"] == "open"

    # Coordinator approves
    coord_client = _auth_client(
        stub_iam,
        user_id=101,
        permissions=("gymkhana.club.manage",),
    )
    appr_resp = coord_client.post(f"/api/v1/gymkhana/memberships/{mem_id}/approve/")
    assert appr_resp.status_code == 200
    assert appr_resp.data["status"] == "confirmed"


def test_voting_poll_and_vote_api(stub_iam):
    club = Club.objects.create(name="Film Club", category="Cultural", status="confirmed")
    ClubLeadership.objects.create(
        club=club,
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=501,
        is_active=True,
    )

    coord_client = _auth_client(
        stub_iam,
        user_id=101,
        permissions=("gymkhana.poll.vote", "gymkhana.club.manage"),
    )
    poll_resp = coord_client.post(
        "/api/v1/gymkhana/polls/",
        {
            "club_id": club.id,
            "title": "Movie Selection",
            "description": "Choose Friday movie",
            "options": ["Interstellar", "Inception"],
            "expires_at": "2099-01-01T00:00:00Z",
            "target_batch": "ALL",
            "target_branch": "ALL",
        },
        format="json",
    )
    assert poll_resp.status_code == 201
    poll_id = poll_resp.data["id"]
    option_id = poll_resp.data["options"][0]["id"]

    # Student votes
    student_client = _auth_client(
        stub_iam,
        user_id=301,
        permissions=("gymkhana.poll.vote",),
    )
    vote_resp = student_client.post(
        f"/api/v1/gymkhana/polls/{poll_id}/vote/",
        {
            "option_id": option_id,
            "student_batch": "2024",
            "student_branch": "CSE",
        },
        format="json",
    )
    assert vote_resp.status_code == 201


def test_contracts_plural_getters():
    club = Club.objects.create(name="Tech Club", category="Technical", status="confirmed")
    ClubLeadership.objects.create(
        club=club,
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=501,
        is_active=True,
    )
    ClubMembership.objects.create(club=club, student_id=401, status="confirmed")
    VenueBooking.objects.create(
        club=club,
        booking_type="session",
        venue_name="L101 Lecture Hall",
        booking_date=date(2026, 12, 10),
        start_time=time(9, 0),
        end_time=time(11, 0),
        created_by_id=101,
    )

    clubs = get_clubs([club.id])
    assert len(clubs) == 1
    assert clubs[0]["name"] == "Tech Club"

    leaderships = get_active_leaderships([club.id])
    assert len(leaderships) == 1
    assert leaderships[0]["coordinator_id"] == 101

    mems = get_memberships([401])
    assert len(mems) == 1
    assert mems[0]["student_id"] == 401

    bookings = get_venue_bookings(["L101 Lecture Hall"], [date(2026, 12, 10)])
    assert len(bookings) == 1
    assert bookings[0]["venue_name"] == "L101 Lecture Hall"
