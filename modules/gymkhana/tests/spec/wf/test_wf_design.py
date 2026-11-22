"""Executable pytest cases for the frozen WF_DESIGN.json workflows."""
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.gymkhana.domain import state_machine as sm
from modules.gymkhana.models import (
    Booking,
    BudgetRequest,
    Club,
    EventReport,
    LeadershipAssignment,
    Membership,
    NotificationOutbox,
    Poll,
    Vote,
)
from modules.gymkhana.tests.conftest import (
    CO_COORD,
    COORD,
    COUNCILLOR,
    DRIVE,
    MEMBER,
    PLAIN,
    event_body,
    join,
    make_club,
    poll_body,
    session_body,
)

pytestmark = pytest.mark.django_db
API = "/api/v1/gymkhana"


def club_body(**changes):
    body = {
        "name": "WF Robotics",
        "category": "technical",
        "description": "Build robots.",
        "coordinator_user_id": COORD,
        "co_coordinator_user_id": CO_COORD,
        "faculty_councillor_user_id": COUNCILLOR,
    }
    body.update(changes)
    return body


def report_body(club_id, **changes):
    body = {
        "club_id": club_id,
        "student_incharge_user_id": MEMBER,
        "event_name": "RoboWars",
        "event_at": (timezone.now() - timedelta(days=1)).isoformat(),
        "description": "Went well",
        "report_url": DRIVE,
    }
    body.update(changes)
    return body


def test_gym_001(actors):
    """GYM-001; WF-GYM-03 transition 1 / UC-GYM-001."""
    response = actors.admin().post(f"{API}/clubs/create", club_body(), format="json")
    assert response.status_code == 201
    club = Club.objects.get(pk=response.json()["id"])
    assert club.status == sm.OPEN
    assert sorted(club.leaders.values_list("user_id", flat=True)) == [COORD, CO_COORD]
    assert club.faculty_councillor_user_id == COUNCILLOR


def test_gym_002(actors):
    """GYM-002; WF-GYM-03 transition 2 / UC-GYM-011."""
    club = make_club("WF Pending", status=sm.OPEN)
    response = actors.admin().post(f"{API}/clubs/{club.pk}/approve")
    assert response.status_code == 200
    club.refresh_from_db()
    assert club.status == sm.CONFIRMED


def test_gym_003(actors):
    """GYM-003; BR-GYM-002 condition-false / UC-GYM-001."""
    before = Club.objects.count()
    response = actors.admin().post(
        f"{API}/clubs/create", club_body(coordinator_user_id=COUNCILLOR), format="json"
    )
    assert response.status_code == 422
    assert Club.objects.count() == before


def test_gym_004(actors):
    """GYM-004; BR-GYM-003 condition-false / UC-GYM-001."""
    before = Club.objects.count()
    response = actors.admin().post(
        f"{API}/clubs/create", club_body(faculty_councillor_user_id=PLAIN), format="json"
    )
    assert response.status_code == 422
    assert Club.objects.count() == before


def test_gym_005(actors):
    """GYM-005; BR-GYM-003 condition-false / UC-GYM-001."""
    before = Club.objects.count()
    response = actors.admin().post(
        f"{API}/clubs/create", club_body(category="literary"), format="json"
    )
    assert response.status_code == 422
    assert Club.objects.count() == before


def test_gym_006(actors, club):
    """GYM-006; WF-GYM-01 transition 1 / UC-GYM-004."""
    response = actors.student(PLAIN).post(
        f"{API}/memberships/apply", {"club_id": club.pk, "description": "Achievements"},
        format="json",
    )
    assert response.status_code == 201
    membership = Membership.objects.get(pk=response.json()["id"])
    assert membership.user_id == PLAIN and membership.status == sm.OPEN


def test_gym_007(actors):
    """GYM-007; BR-GYM-007 condition-false / UC-GYM-004."""
    club = make_club("WF Open", status=sm.OPEN)
    before = Membership.objects.count()
    response = actors.student(PLAIN).post(
        f"{API}/memberships/apply", {"club_id": club.pk, "description": "x"},
        format="json",
    )
    assert response.status_code == 404
    assert Membership.objects.count() == before


def test_gym_008(actors, club):
    """GYM-008; BR-GYM-008 condition-false / UC-GYM-004."""
    join(club, PLAIN)
    before = Membership.objects.count()
    response = actors.student(PLAIN).post(
        f"{API}/memberships/apply", {"club_id": club.pk, "description": "again"},
        format="json",
    )
    assert response.status_code == 409
    assert Membership.objects.count() == before


def test_gym_009(actors, club, other_club):
    """GYM-009; BR-GYM-009 / UC-GYM-004."""
    join(club, PLAIN)
    response = actors.student(PLAIN).post(
        f"{API}/memberships/apply", {"club_id": other_club.pk, "description": "y"},
        format="json",
    )
    assert response.status_code == 201
    assert Membership.objects.get(pk=response.json()["id"]).club_id == other_club.pk


def test_gym_010(actors, club):
    """GYM-010; WF-GYM-01 transition 2 / UC-GYM-005."""
    membership = join(club, PLAIN, status=sm.OPEN)
    response = actors.student(COORD).post(
        f"{API}/memberships/approve", {"ids": [membership.pk], "remarks": "Welcome"},
        format="json",
    )
    assert response.status_code == 200
    membership.refresh_from_db()
    assert membership.status == sm.CONFIRMED


def test_gym_011(actors, club, other_club):
    """GYM-011; BR-GYM-010 condition-false / UC-GYM-005."""
    membership = join(other_club, MEMBER, status=sm.OPEN)
    before = membership.status
    response = actors.student(COORD).post(
        f"{API}/memberships/approve", {"ids": [membership.pk]}, format="json"
    )
    assert response.status_code == 200
    membership.refresh_from_db()
    assert membership.status == before == sm.OPEN


def test_gym_012(actors, club):
    """GYM-012; WF-GYM-02 transition 1 / UC-GYM-006."""
    join(club, MEMBER)
    response = actors.student(COORD).post(
        f"{API}/polls/create", poll_body(club.pk), format="json"
    )
    assert response.status_code == 201
    poll = Poll.objects.get(pk=response.json()["id"])
    assert poll.expires_on > timezone.localdate()
    assert poll.choices.count() >= 2 and poll.targets.exists()
    assert NotificationOutbox.objects.filter(is_broadcast=True).exists()


def test_gym_013(actors, club):
    """GYM-013; BR-GYM-012 condition-false / UC-GYM-006."""
    before = Poll.objects.count()
    response = actors.student(COORD).post(
        f"{API}/polls/create", poll_body(club.pk, choices=["Only"]), format="json"
    )
    assert response.status_code == 422
    assert Poll.objects.count() == before


def test_gym_014(actors, club):
    """GYM-014; WF-GYM-02 transition 2 / UC-GYM-007."""
    poll = actors.student(COORD).post(
        f"{API}/polls/create", poll_body(club.pk), format="json"
    ).json()
    response = actors.student(PLAIN).post(
        f"{API}/polls/{poll['id']}/votes", {"choice_id": poll["choices"][0]["id"]},
        format="json",
    )
    assert response.status_code == 201
    vote = Vote.objects.get(pk=response.json()["id"])
    assert vote.poll_id == poll["id"] and vote.user_id == PLAIN


def test_gym_015(actors, club):
    """GYM-015; BR-GYM-014 condition-false / UC-GYM-007."""
    poll = actors.student(COORD).post(
        f"{API}/polls/create", poll_body(club.pk), format="json"
    ).json()
    Poll.objects.filter(pk=poll["id"]).update(
        expires_on=timezone.localdate() - timedelta(days=1)
    )
    before = Vote.objects.count()
    response = actors.student(PLAIN).post(
        f"{API}/polls/{poll['id']}/votes", {"choice_id": poll["choices"][0]["id"]},
        format="json",
    )
    assert response.status_code == 409
    assert Vote.objects.count() == before


def test_gym_016(actors, club):
    """GYM-016; BR-GYM-013 condition-false / UC-GYM-007."""
    poll = actors.student(COORD).post(
        f"{API}/polls/create", poll_body(club.pk), format="json"
    ).json()
    before = Vote.objects.count()
    response = actors.student(1010).post(
        f"{API}/polls/{poll['id']}/votes", {"choice_id": poll["choices"][0]["id"]},
        format="json",
    )
    assert response.status_code == 404
    assert Vote.objects.count() == before


def test_gym_017(actors, club):
    """GYM-017; BR-GYM-015 condition-false / UC-GYM-007."""
    poll = actors.student(COORD).post(
        f"{API}/polls/create", poll_body(club.pk), format="json"
    ).json()
    student = actors.student(PLAIN)
    vote_body = {"choice_id": poll["choices"][0]["id"]}
    assert student.post(f"{API}/polls/{poll['id']}/votes", vote_body, format="json").status_code == 201
    before = Vote.objects.count()
    response = student.post(f"{API}/polls/{poll['id']}/votes", vote_body, format="json")
    assert response.status_code == 409
    assert Vote.objects.count() == before


def test_gym_018(actors, club, venues):
    """GYM-018; Problem Statement 4.1 / Book Club Session."""
    join(club, MEMBER)
    response = actors.student(COORD).post(
        f"{API}/sessions", session_body(club.pk), format="json"
    )
    assert response.status_code == 201
    booking = Booking.objects.get(pk=response.json()["id"])
    assert booking.kind == "session" and booking.start_time < booking.end_time
    assert NotificationOutbox.objects.filter(
        topic="session.booked", recipient_user_id=MEMBER
    ).exists()


def test_gym_019(actors, club, venues):
    """GYM-019; Problem Statement 6 / booking start time."""
    before = Booking.objects.count()
    response = actors.student(COORD).post(
        f"{API}/sessions", session_body(club.pk, start="11:00", end="11:00"),
        format="json",
    )
    assert response.status_code == 422
    assert Booking.objects.count() == before


def test_gym_020(actors, club, venues):
    """GYM-020; Problem Statement 4.1 / Book Club Event."""
    join(club, MEMBER)
    response = actors.student(COORD).post(
        f"{API}/events", event_body(club.pk), format="json"
    )
    assert response.status_code == 201
    booking = Booking.objects.get(pk=response.json()["id"])
    assert booking.kind == "event" and booking.start_time < booking.end_time
    assert NotificationOutbox.objects.filter(
        topic="event.booked", recipient_user_id=MEMBER
    ).exists()


def test_gym_021(actors, club, venues):
    """GYM-021; Problem Statement 6 / no overlapping booking."""
    head = actors.student(COORD)
    first = head.post(f"{API}/sessions", session_body(club.pk), format="json")
    assert first.status_code == 201
    before = Booking.objects.count()
    response = head.post(
        f"{API}/events", event_body(club.pk, start="10:30", end="11:30"), format="json"
    )
    assert response.status_code == 409
    assert Booking.objects.count() == before


def test_gym_022(actors, club):
    """GYM-022; Problem Statement 4.1 / Change Club Leadership."""
    response = actors.student(COORD).post(
        f"{API}/clubs/{club.pk}/leadership",
        {"coordinator_user_id": MEMBER, "co_coordinator_user_id": PLAIN},
        format="json",
    )
    assert response.status_code == 200
    current = LeadershipAssignment.objects.filter(club=club, valid_to__isnull=True)
    assert sorted(current.values_list("user_id", flat=True)) == [MEMBER, PLAIN]


def test_gym_023(actors, club):
    """GYM-023; Problem Statement 4.1 / Request Club Budget."""
    response = actors.student(COORD).post(
        f"{API}/budget-requests/create",
        {"club_id": club.pk, "purpose": "Parts", "amount": "10.00",
         "document_url": DRIVE, "description": "Motors"},
        format="json",
    )
    assert response.status_code == 201
    request = BudgetRequest.objects.get(pk=response.json()["id"])
    assert request.document_link == DRIVE and request.amount >= 0


def test_gym_024(actors, club):
    """GYM-024; Problem Statement 6 / club budget amount."""
    before = BudgetRequest.objects.count()
    response = actors.student(COORD).post(
        f"{API}/budget-requests/create",
        {"club_id": club.pk, "purpose": "Parts", "amount": "-1",
         "document_url": DRIVE},
        format="json",
    )
    assert response.status_code == 422
    assert BudgetRequest.objects.count() == before


def test_gym_025(actors, club):
    """GYM-025; Problem Statement 6 / budget supporting file."""
    before = BudgetRequest.objects.count()
    response = actors.student(COORD).post(
        f"{API}/budget-requests/create",
        {"club_id": club.pk, "purpose": "Parts", "amount": "10.00",
         "document_url": ""},
        format="json",
    )
    assert response.status_code == 422
    assert BudgetRequest.objects.count() == before


def test_gym_026(actors, club):
    """GYM-026; Problem Statement 4.1 / Submit Club Event Report."""
    response = actors.student(COORD).post(
        f"{API}/event-reports/create", report_body(club.pk), format="json"
    )
    assert response.status_code == 201
    report = EventReport.objects.get(pk=response.json()["id"])
    assert report.report_link == DRIVE
    faculty = actors.faculty(COUNCILLOR)
    assert faculty.get(f"{API}/event-reports/{report.pk}").status_code == 200


def test_gym_027(actors, club):
    """GYM-027; Problem Statement 6 / event report file."""
    before = EventReport.objects.count()
    response = actors.student(COORD).post(
        f"{API}/event-reports/create", report_body(club.pk, report_url=""),
        format="json",
    )
    assert response.status_code == 422
    assert EventReport.objects.count() == before
