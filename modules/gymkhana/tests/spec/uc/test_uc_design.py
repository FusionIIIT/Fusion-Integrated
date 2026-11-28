"""Executable tests for the frozen UC_DESIGN.json cases."""
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
    OTHER_FACULTY,
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
    body = {"name": "UC Robotics", "category": "technical", "description": "Build robots.",
            "coordinator_user_id": COORD, "co_coordinator_user_id": CO_COORD,
            "faculty_councillor_user_id": COUNCILLOR}
    body.update(changes)
    return body


def report_body(club_id, **changes):
    body = {"club_id": club_id, "student_incharge_user_id": MEMBER,
            "event_name": "RoboWars", "event_at": (timezone.now() - timedelta(days=1)).isoformat(),
            "description": "Went well", "report_url": DRIVE}
    body.update(changes)
    return body


def test_tc_uc_gym_001_main(actors):
    """TC-UC-GYM-001-MAIN; UC-GYM-001 Main Success Scenario."""
    r = actors.admin().post(f"{API}/clubs/create", club_body(), format="json")
    assert r.status_code == 201
    club = Club.objects.get(pk=r.json()["id"])
    assert club.status == sm.OPEN
    assert sorted(club.leaders.values_list("user_id", flat=True)) == [COORD, CO_COORD]
    assert club.faculty_councillor_user_id == COUNCILLOR


def test_tc_uc_gym_001_alt(actors):
    """TC-UC-GYM-001-ALT; UC-GYM-001 Alternative Flows."""
    r = actors.admin().post(f"{API}/clubs/create", club_body(coordinator_user_id=COUNCILLOR),
                            format="json")
    assert r.status_code == 422
    assert not Club.objects.exists()
    r = actors.admin().post(f"{API}/clubs/create", club_body(), format="json")
    assert r.status_code == 201


@pytest.mark.skip(reason="NOT_AUTOMATED: no supported real storage outage interface; simulating database failure would mock the behavior under test.")
def test_tc_uc_gym_001_exc():
    """TC-UC-GYM-001-EXC; UC-GYM-001 Exception Flows."""


def test_tc_uc_gym_002_main(actors, club, venues):
    """TC-UC-GYM-002-MAIN; UC-GYM-002 Main Success Scenario."""
    join(club, MEMBER)
    r = actors.student(COORD).post(f"{API}/sessions", session_body(club.pk), format="json")
    assert r.status_code == 201
    booking = Booking.objects.get(pk=r.json()["id"])
    assert booking.kind == "session" and booking.venue_name == "LHTC 101"
    assert NotificationOutbox.objects.filter(topic="session.booked", recipient_user_id=MEMBER).exists()


def test_tc_uc_gym_002_alt(actors, club, venues):
    """TC-UC-GYM-002-ALT; UC-GYM-002 Alternative Flows."""
    head = actors.student(COORD)
    assert head.post(f"{API}/events", event_body(club.pk), format="json").status_code == 201
    before = Booking.objects.count()
    r = head.post(f"{API}/sessions", session_body(club.pk, start="10:30", end="11:30"), format="json")
    assert r.status_code == 409
    assert Booking.objects.count() == before


def test_tc_uc_gym_002_exc(actors, club, venues):
    """TC-UC-GYM-002-EXC; UC-GYM-002 Exception Flows."""
    r = actors.student(COORD).post(f"{API}/sessions", session_body(club.pk, venue="Basement"), format="json")
    assert r.status_code == 422
    assert not Booking.objects.exists()


def test_tc_uc_gym_003_main(actors, club, venues):
    """TC-UC-GYM-003-MAIN; UC-GYM-003 Main Success Scenario."""
    join(club, MEMBER)
    r = actors.student(COORD).post(f"{API}/events", event_body(club.pk), format="json")
    assert r.status_code == 201
    booking = Booking.objects.get(pk=r.json()["id"])
    assert booking.kind == "event" and booking.faculty_user_id == COUNCILLOR
    assert NotificationOutbox.objects.filter(topic="event.booked", recipient_user_id=MEMBER).exists()


def test_tc_uc_gym_003_alt(actors, club, venues):
    """TC-UC-GYM-003-ALT; UC-GYM-003 Alternative Flows."""
    head = actors.student(COORD)
    assert head.post(f"{API}/sessions", session_body(club.pk), format="json").status_code == 201
    before = Booking.objects.count()
    r = head.post(f"{API}/events", event_body(club.pk, start="10:30", end="11:30"), format="json")
    assert r.status_code == 409
    assert Booking.objects.count() == before


def test_tc_uc_gym_003_exc(actors, club, venues):
    """TC-UC-GYM-003-EXC; UC-GYM-003 Exception Flows."""
    r = actors.student(COORD).post(f"{API}/events", event_body(club.pk, venue="Basement"), format="json")
    assert r.status_code == 422
    assert not Booking.objects.exists()


def test_tc_uc_gym_004_main(actors, club):
    """TC-UC-GYM-004-MAIN; UC-GYM-004 Main Success Scenario."""
    r = actors.student(PLAIN).post(f"{API}/memberships/apply", {"club_id": club.pk, "description": "Achievements"}, format="json")
    assert r.status_code == 201
    app = Membership.objects.get(pk=r.json()["id"])
    assert app.user_id == PLAIN and app.status == sm.OPEN


def test_tc_uc_gym_004_alt(actors, club, other_club):
    """TC-UC-GYM-004-ALT; UC-GYM-004 Alternative Flows."""
    student = actors.student(PLAIN)
    assert student.post(f"{API}/memberships/apply", {"club_id": club.pk, "description": "x"}, format="json").status_code == 201
    r = student.post(f"{API}/memberships/apply", {"club_id": other_club.pk, "description": "y"}, format="json")
    assert r.status_code == 201 and r.json()["status"] == "open"


def test_tc_uc_gym_004_exc(actors, club):
    """TC-UC-GYM-004-EXC; UC-GYM-004 Exception Flows."""
    student = actors.student(PLAIN)
    first = student.post(f"{API}/memberships/apply", {"club_id": club.pk, "description": "original"}, format="json")
    before = Membership.objects.count()
    r = student.post(f"{API}/memberships/apply", {"club_id": club.pk, "description": "duplicate"}, format="json")
    assert r.status_code == 409 and Membership.objects.count() == before
    assert Membership.objects.get(pk=first.json()["id"]).description == "original"


def test_tc_uc_gym_005_main(actors, club):
    """TC-UC-GYM-005-MAIN; UC-GYM-005 Main Success Scenario."""
    app = join(club, PLAIN, status=sm.OPEN)
    r = actors.student(COORD).post(f"{API}/memberships/approve", {"ids": [app.pk], "remarks": "Welcome"}, format="json")
    assert r.status_code == 200
    app.refresh_from_db()
    assert app.status == sm.CONFIRMED and app.remarks == "Welcome"


def test_tc_uc_gym_005_alt(actors, club):
    """TC-UC-GYM-005-ALT; UC-GYM-005 Alternative Flows."""
    first, second = join(club, PLAIN, status=sm.OPEN), join(club, MEMBER, status=sm.OPEN)
    r = actors.student(COORD).post(f"{API}/memberships/approve", {"ids": [first.pk, second.pk]}, format="json")
    assert r.status_code == 200
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.status == sm.CONFIRMED and second.status == sm.CONFIRMED


def test_tc_uc_gym_005_exc(actors, club, other_club):
    """TC-UC-GYM-005-EXC; UC-GYM-005 Exception Flows."""
    app = join(other_club, MEMBER, status=sm.OPEN)
    before = app.status
    r = actors.student(COORD).post(f"{API}/memberships/approve", {"ids": [app.pk]}, format="json")
    assert r.status_code == 200
    app.refresh_from_db()
    assert app.status == before


def test_tc_uc_gym_006_main(actors, club):
    """TC-UC-GYM-006-MAIN; UC-GYM-006 Main Success Scenario."""
    join(club, MEMBER)
    r = actors.student(COORD).post(f"{API}/polls/create", poll_body(club.pk), format="json")
    assert r.status_code == 201
    poll = Poll.objects.get(pk=r.json()["id"])
    assert poll.choices.count() >= 2 and poll.targets.get().batch_year == 2023
    assert NotificationOutbox.objects.filter(is_broadcast=True).exists()


def test_tc_uc_gym_006_alt(actors, club):
    """TC-UC-GYM-006-ALT; UC-GYM-006 Alternative Flows."""
    body = poll_body(club.pk, targets=[{"batch_year": 2024, "discipline": ""}])
    r = actors.student(COORD).post(f"{API}/polls/create", body, format="json")
    assert r.status_code == 201
    assert [p["id"] for p in actors.student(1010).get(f"{API}/polls").json()["results"]] == [r.json()["id"]]


def test_tc_uc_gym_006_exc(actors, club):
    """TC-UC-GYM-006-EXC; UC-GYM-006 Exception Flows."""
    r = actors.student(COORD).post(f"{API}/polls/create", poll_body(club.pk, choices=["Only"]), format="json")
    assert r.status_code == 422
    assert not Poll.objects.exists()


def test_tc_uc_gym_007_main(actors, club):
    """TC-UC-GYM-007-MAIN; UC-GYM-007 Main Success Scenario."""
    poll = actors.student(COORD).post(f"{API}/polls/create", poll_body(club.pk), format="json").json()
    r = actors.student(PLAIN).post(f"{API}/polls/{poll['id']}/votes", {"choice_id": poll["choices"][0]["id"]}, format="json")
    assert r.status_code == 201 and Vote.objects.count() == 1
    managed = actors.student(COORD).get(f"{API}/polls/managed").json()["results"][0]
    assert managed["total_votes"] == 1


def test_tc_uc_gym_007_exc(actors, club):
    """TC-UC-GYM-007-EXC; UC-GYM-007 Exception Flows."""
    poll = actors.student(COORD).post(f"{API}/polls/create", poll_body(club.pk), format="json").json()
    outsider = actors.student(1010)
    before = Vote.objects.count()
    r = outsider.post(f"{API}/polls/{poll['id']}/votes", {"choice_id": poll["choices"][0]["id"]}, format="json")
    assert r.status_code == 404 and Vote.objects.count() == before


def test_tc_uc_gym_008_main(actors, club):
    """TC-UC-GYM-008-MAIN; UC-GYM-008 Main Success Scenario."""
    r = actors.student(COORD).post(f"{API}/clubs/{club.pk}/leadership", {"coordinator_user_id": MEMBER, "co_coordinator_user_id": PLAIN}, format="json")
    assert r.status_code == 200
    current = LeadershipAssignment.objects.filter(club=club, valid_to__isnull=True)
    assert sorted(current.values_list("user_id", flat=True)) == [MEMBER, PLAIN]
    assert LeadershipAssignment.objects.filter(club=club, valid_to__isnull=False).count() == 2


def test_tc_uc_gym_008_exc(actors, club):
    """TC-UC-GYM-008-EXC; UC-GYM-008 Exception Flows."""
    before = list(LeadershipAssignment.objects.filter(club=club, valid_to__isnull=True).values_list("user_id", flat=True))
    r = actors.student(COORD).post(f"{API}/clubs/{club.pk}/leadership", {"coordinator_user_id": COUNCILLOR, "co_coordinator_user_id": PLAIN}, format="json")
    assert r.status_code == 422
    assert list(LeadershipAssignment.objects.filter(club=club, valid_to__isnull=True).values_list("user_id", flat=True)) == before


def test_tc_uc_gym_009_main(actors, club):
    """TC-UC-GYM-009-MAIN; UC-GYM-009 Main Success Scenario."""
    r = actors.student(COORD).post(f"{API}/budget-requests/create", {"club_id": club.pk, "purpose": "Parts", "amount": "10.00", "document_url": DRIVE, "description": "Motors"}, format="json")
    assert r.status_code == 201
    request = BudgetRequest.objects.get(pk=r.json()["id"])
    assert request.status == sm.OPEN and request.document_link == DRIVE


def test_tc_uc_gym_009_exc(actors, club):
    """TC-UC-GYM-009-EXC; UC-GYM-009 Exception Flows."""
    r = actors.student(COORD).post(f"{API}/budget-requests/create", {"club_id": club.pk, "purpose": "Parts", "amount": "-1", "document_url": DRIVE}, format="json")
    assert r.status_code == 422 and not BudgetRequest.objects.exists()


def test_tc_uc_gym_010_main(actors, club):
    """TC-UC-GYM-010-MAIN; UC-GYM-010 Main Success Scenario."""
    r = actors.student(COORD).post(f"{API}/event-reports/create", report_body(club.pk), format="json")
    assert r.status_code == 201
    report = EventReport.objects.get(pk=r.json()["id"])
    assert report.report_link == DRIVE and report.student_incharge_user_id == MEMBER


def test_tc_uc_gym_010_exc(actors, club):
    """TC-UC-GYM-010-EXC; UC-GYM-010 Exception Flows."""
    r = actors.student(COORD).post(f"{API}/event-reports/create", report_body(club.pk, report_url=""), format="json")
    assert r.status_code == 422 and not EventReport.objects.exists()


def test_tc_uc_gym_011_main(actors):
    """TC-UC-GYM-011-MAIN; UC-GYM-011 Main Success Scenario."""
    club = make_club("Pending UC", status=sm.OPEN)
    r = actors.admin().post(f"{API}/clubs/{club.pk}/approve")
    assert r.status_code == 200
    club.refresh_from_db()
    assert club.status == sm.CONFIRMED


def test_tc_uc_gym_011_exc(actors, club):
    """TC-UC-GYM-011-EXC; UC-GYM-011 Exception Flows."""
    r = actors.admin().post(f"{API}/clubs/{club.pk}/approve")
    assert r.status_code == 409
    club.refresh_from_db()
    assert club.status == sm.CONFIRMED


def test_tc_uc_gym_012_main(actors, club):
    """TC-UC-GYM-012-MAIN; UC-GYM-012 Main Success Scenario."""
    created = actors.student(COORD).post(f"{API}/event-reports/create", report_body(club.pk), format="json")
    rid = created.json()["id"]
    faculty = actors.faculty(COUNCILLOR)
    assert [r["id"] for r in faculty.get(f"{API}/event-reports").json()["results"]] == [rid]
    detail = faculty.get(f"{API}/event-reports/{rid}")
    assert detail.status_code == 200 and detail.json()["report_link"] == DRIVE


def test_tc_uc_gym_012_exc(actors, club):
    """TC-UC-GYM-012-EXC; UC-GYM-012 Exception Flows."""
    created = actors.student(COORD).post(f"{API}/event-reports/create", report_body(club.pk), format="json")
    outsider = actors.faculty(OTHER_FACULTY)
    assert outsider.get(f"{API}/event-reports").json()["results"] == []
    assert outsider.get(f"{API}/event-reports/{created.json()['id']}").status_code == 404
