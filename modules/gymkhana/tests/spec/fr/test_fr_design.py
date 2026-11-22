"""Executable cases from the frozen FR (functional requirements) design."""
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
        "name": "French Robotics",
        "category": "technical",
        "description": "Builds robots.",
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


def test_gym_afr_001_afr_gym_001_club_creation(actors):
    """GYM-AFR-001 / AFR-GYM-001: create a fully assigned club."""
    response = actors.admin().post(f"{API}/clubs/create", club_body(), format="json")
    assert response.status_code == 201
    club = Club.objects.get(pk=response.json()["id"])
    assert (club.name, club.category, club.description, club.status) == (
        "French Robotics", "technical", "Builds robots.", sm.OPEN
    )
    assert sorted(club.leaders.values_list("user_id", flat=True)) == [COORD, CO_COORD]
    assert club.faculty_councillor_user_id == COUNCILLOR


def test_gym_afr_002_afr_gym_002_student_leader_validation(actors):
    """GYM-AFR-002 / AFR-GYM-002: invalid leader assignment is refused unchanged."""
    before = Club.objects.count()
    response = actors.admin().post(
        f"{API}/clubs/create", club_body(coordinator_user_id=COUNCILLOR), format="json"
    )
    assert response.status_code == 422
    assert Club.objects.count() == before


def test_gym_afr_003_afr_gym_003_faculty_validation(actors):
    """GYM-AFR-003 / AFR-GYM-003: non-faculty councillor is refused unchanged."""
    response = actors.admin().post(
        f"{API}/clubs/create", club_body(faculty_councillor_user_id=PLAIN), format="json"
    )
    assert response.status_code == 422
    assert not Club.objects.exists()


def test_gym_afr_004_afr_gym_004_category_restriction(actors):
    """GYM-AFR-004 / AFR-GYM-004: disallowed category is refused unchanged."""
    response = actors.admin().post(
        f"{API}/clubs/create", club_body(category="Literary"), format="json"
    )
    assert response.status_code == 422
    assert not Club.objects.exists()


def test_gym_afr_005_afr_gym_005_initial_open_status(actors):
    """GYM-AFR-005 / AFR-GYM-005: a new club starts open."""
    response = actors.admin().post(f"{API}/clubs/create", club_body(), format="json")
    assert response.status_code == 201
    assert Club.objects.get(pk=response.json()["id"]).status == sm.OPEN


def test_gym_afr_006_afr_gym_006_approve_open_club(actors):
    """GYM-AFR-006 / AFR-GYM-006: Student Admin approves an open club."""
    club = make_club("Awaiting Approval", status=sm.OPEN)
    response = actors.admin().post(f"{API}/clubs/{club.pk}/approve")
    assert response.status_code == 200
    club.refresh_from_db()
    assert club.status == sm.CONFIRMED


def test_gym_afr_007_afr_gym_007_leadership_replacement(actors, club):
    """GYM-AFR-007 / AFR-GYM-007: club head replaces both leadership assignments."""
    response = actors.student(COORD).post(
        f"{API}/clubs/{club.pk}/leadership",
        {"coordinator_user_id": MEMBER, "co_coordinator_user_id": PLAIN},
        format="json",
    )
    assert response.status_code == 200
    current = LeadershipAssignment.objects.filter(club=club, valid_to__isnull=True)
    assert sorted(current.values_list("user_id", flat=True)) == [MEMBER, PLAIN]


def test_gym_afr_008_afr_gym_008_leadership_student_validation(actors, club):
    """GYM-AFR-008 / AFR-GYM-008: invalid replacement is refused without changes."""
    response = actors.student(COORD).post(
        f"{API}/clubs/{club.pk}/leadership",
        {"coordinator_user_id": COUNCILLOR, "co_coordinator_user_id": PLAIN},
        format="json",
    )
    assert response.status_code == 422
    assert sorted(
        LeadershipAssignment.objects.filter(club=club, valid_to__isnull=True)
        .values_list("user_id", flat=True)
    ) == [COORD, CO_COORD]


def test_gym_afr_009_afr_gym_009_current_leadership_assignments(actors, club):
    """GYM-AFR-009 / AFR-GYM-009: only the replacements remain active."""
    actors.student(COORD).post(
        f"{API}/clubs/{club.pk}/leadership",
        {"coordinator_user_id": MEMBER, "co_coordinator_user_id": PLAIN},
        format="json",
    )
    assert sorted(
        LeadershipAssignment.objects.filter(club=club, valid_to__isnull=True)
        .values_list("user_id", flat=True)
    ) == [MEMBER, PLAIN]


def test_gym_afr_010_afr_gym_010_session_booking(actors, club, venues):
    """GYM-AFR-010 / AFR-GYM-010: create a session with its submitted details."""
    response = actors.student(COORD).post(
        f"{API}/sessions", session_body(club.pk), format="json"
    )
    assert response.status_code == 201
    booking = Booking.objects.get(pk=response.json()["id"])
    assert (booking.kind, booking.venue_name, booking.description) == (
        "session", "LHTC 101", "Weekly build"
    )


def test_gym_afr_011_afr_gym_011_valid_time_range(actors, club, venues):
    """GYM-AFR-011 / AFR-GYM-011: equal/reversed range refuses and creates nothing."""
    before = Booking.objects.count()
    for start, end in (("10:00", "10:00"), ("11:00", "10:00")):
        response = actors.student(COORD).post(
            f"{API}/sessions", session_body(club.pk, start=start, end=end), format="json"
        )
        assert response.status_code == 422
        assert Booking.objects.count() == before


def test_gym_afr_012_afr_gym_012_cross_type_venue_conflict(actors, club, venues):
    """GYM-AFR-012 / AFR-GYM-012: overlapping session/event venue slot is refused."""
    head = actors.student(COORD)
    assert head.post(f"{API}/sessions", session_body(club.pk), format="json").status_code == 201
    before = Booking.objects.count()
    response = head.post(
        f"{API}/events", event_body(club.pk, start="10:30", end="11:30"), format="json"
    )
    assert response.status_code == 409
    assert Booking.objects.count() == before


def test_gym_afr_013_afr_gym_013_session_notification(actors, club, venues):
    """GYM-AFR-013 / AFR-GYM-013: confirmed members get the session notice."""
    join(club, MEMBER)
    join(club, PLAIN, status=sm.OPEN)
    response = actors.student(COORD).post(
        f"{API}/sessions", session_body(club.pk), format="json"
    )
    assert response.status_code == 201
    assert list(NotificationOutbox.objects.filter(topic="session.booked")
                .values_list("recipient_user_id", flat=True)) == [MEMBER]


def test_gym_afr_014_afr_gym_014_event_booking(actors, club, venues):
    """GYM-AFR-014 / AFR-GYM-014: event includes details and club faculty context."""
    response = actors.student(COORD).post(
        f"{API}/events", event_body(club.pk), format="json"
    )
    assert response.status_code == 201
    booking = Booking.objects.get(pk=response.json()["id"])
    assert booking.kind == "event"
    assert booking.event_name == "RoboWars"
    assert booking.faculty_user_id == COUNCILLOR
    assert booking.poster_link == DRIVE


def test_gym_afr_015_afr_gym_015_event_notification(actors, club, venues):
    """GYM-AFR-015 / AFR-GYM-015: confirmed member gets the event notice."""
    join(club, MEMBER)
    response = actors.student(COORD).post(
        f"{API}/events", event_body(club.pk), format="json"
    )
    assert response.status_code == 201
    assert NotificationOutbox.objects.filter(
        topic="event.booked", recipient_user_id=MEMBER
    ).exists()


def test_gym_afr_016_afr_gym_016_confirmed_club_application(actors, club):
    """GYM-AFR-016 / AFR-GYM-016: student can apply to a confirmed club."""
    response = actors.student(PLAIN).post(
        f"{API}/memberships/apply",
        {"club_id": club.pk, "description": "I build drones."},
        format="json",
    )
    assert response.status_code == 201
    assert Membership.objects.get(pk=response.json()["id"]).description == "I build drones."


def test_gym_afr_017_afr_gym_017_applications_to_different_clubs(actors, club, other_club):
    """GYM-AFR-017 / AFR-GYM-017: applications to two clubs are both accepted."""
    student = actors.student(PLAIN)
    for target in (club, other_club):
        response = student.post(
            f"{API}/memberships/apply", {"club_id": target.pk, "description": "x"},
            format="json",
        )
        assert response.status_code == 201
    assert Membership.objects.filter(user_id=PLAIN).count() == 2


def test_gym_afr_018_afr_gym_018_duplicate_same_club_application(actors, club):
    """GYM-AFR-018 / AFR-GYM-018: duplicate is refused and original remains."""
    student = actors.student(PLAIN)
    student.post(f"{API}/memberships/apply", {"club_id": club.pk, "description": "first"},
                 format="json")
    before = Membership.objects.count()
    response = student.post(
        f"{API}/memberships/apply", {"club_id": club.pk, "description": "second"},
        format="json",
    )
    assert response.status_code == 409
    assert Membership.objects.count() == before
    assert Membership.objects.get(user_id=PLAIN).description == "first"


def test_gym_afr_019_afr_gym_019_application_open_status(actors, club):
    """GYM-AFR-019 / AFR-GYM-019: submitted membership application starts open."""
    response = actors.student(PLAIN).post(
        f"{API}/memberships/apply", {"club_id": club.pk, "description": "x"},
        format="json",
    )
    assert response.status_code == 201
    assert Membership.objects.get(pk=response.json()["id"]).status == sm.OPEN


def test_gym_afr_020_afr_gym_020_pending_applications_access(actors, club):
    """GYM-AFR-020 / AFR-GYM-020: club head can access pending applications."""
    application = join(club, PLAIN, status=sm.OPEN)
    response = actors.student(COORD).get(f"{API}/memberships?club={club.pk}&status=open")
    assert response.status_code == 200
    assert [row["id"] for row in response.json()["results"]] == [application.pk]


def test_gym_afr_021_afr_gym_021_approve_open_application(actors, club):
    """GYM-AFR-021 / AFR-GYM-021: approval accepts and records remarks."""
    application = join(club, PLAIN, status=sm.OPEN)
    response = actors.student(COORD).post(
        f"{API}/memberships/approve", {"ids": [application.pk], "remarks": "Welcome"},
        format="json",
    )
    assert response.status_code == 200
    application.refresh_from_db()
    assert application.remarks == "Welcome"


def test_gym_afr_022_afr_gym_022_approved_application_status(actors, club):
    """GYM-AFR-022 / AFR-GYM-022: approved application changes to confirmed."""
    application = join(club, PLAIN, status=sm.OPEN)
    response = actors.student(COORD).post(
        f"{API}/memberships/approve", {"ids": [application.pk]}, format="json"
    )
    assert response.status_code == 200
    application.refresh_from_db()
    assert application.status == sm.CONFIRMED


def test_gym_afr_023_afr_gym_023_poll_creation(actors, club):
    """GYM-AFR-023 / AFR-GYM-023: create poll, choices, expiry, and target groups."""
    response = actors.student(COORD).post(
        f"{API}/polls/create", poll_body(club.pk), format="json"
    )
    assert response.status_code == 201
    poll = Poll.objects.get(pk=response.json()["id"])
    assert poll.title == "Next workshop"
    assert poll.choices.count() == 2
    assert poll.targets.get().batch_year == 2023


def test_gym_afr_024_afr_gym_024_minimum_poll_choices(actors, club):
    """GYM-AFR-024 / AFR-GYM-024: fewer than two choices is refused unchanged."""
    response = actors.student(COORD).post(
        f"{API}/polls/create", poll_body(club.pk, choices=["Only"]), format="json"
    )
    assert response.status_code == 422
    assert not Poll.objects.exists()


def test_gym_afr_025_afr_gym_025_target_group_notification(actors, club):
    """GYM-AFR-025 / AFR-GYM-025: poll creation notifies the selected population."""
    response = actors.student(COORD).post(
        f"{API}/polls/create", poll_body(club.pk), format="json"
    )
    assert response.status_code == 201
    notice = NotificationOutbox.objects.get(is_broadcast=True)
    assert notice.payload["poll_id"] == response.json()["id"]


def test_gym_afr_026_afr_gym_026_active_poll_access(actors, club):
    """GYM-AFR-026 / AFR-GYM-026: eligible student sees the active poll and choices."""
    created = actors.student(COORD).post(
        f"{API}/polls/create", poll_body(club.pk), format="json"
    ).json()
    response = actors.student(PLAIN).get(f"{API}/polls")
    assert response.status_code == 200
    poll = response.json()["results"][0]
    assert poll["id"] == created["id"]
    assert len(poll["choices"]) == 2


def test_gym_afr_027_afr_gym_027_cast_poll_vote(actors, club):
    """GYM-AFR-027 / AFR-GYM-027: eligible student can cast one vote."""
    created = actors.student(COORD).post(
        f"{API}/polls/create", poll_body(club.pk), format="json"
    ).json()
    response = actors.student(PLAIN).post(
        f"{API}/polls/{created['id']}/votes",
        {"choice_id": created["choices"][0]["id"]},
        format="json",
    )
    assert response.status_code == 201
    assert Vote.objects.count() == 1


def test_gym_afr_028_afr_gym_028_one_vote_and_tally(actors, club):
    """GYM-AFR-028 / AFR-GYM-028: second vote refused and accepted vote tallied."""
    created = actors.student(COORD).post(
        f"{API}/polls/create", poll_body(club.pk), format="json"
    ).json()
    voter = actors.student(PLAIN)
    first, second = (choice["id"] for choice in created["choices"])
    voter.post(f"{API}/polls/{created['id']}/votes", {"choice_id": first}, format="json")
    response = voter.post(
        f"{API}/polls/{created['id']}/votes", {"choice_id": second}, format="json"
    )
    assert response.status_code == 409
    assert list(Vote.objects.values_list("choice_id", flat=True)) == [first]
    tally = actors.student(COORD).get(f"{API}/polls/managed").json()["results"][0]
    assert tally["total_votes"] == 1


def test_gym_afr_029_afr_gym_029_budget_request_submission(actors, club):
    """GYM-AFR-029 / AFR-GYM-029: submit budget request with file and details."""
    response = actors.student(COORD).post(
        f"{API}/budget-requests/create",
        {"club_id": club.pk, "purpose": "Parts", "description": "Motors",
         "amount": "10.00", "document_url": DRIVE},
        format="json",
    )
    assert response.status_code == 201
    assert BudgetRequest.objects.get(pk=response.json()["id"]).document_link == DRIVE


def test_gym_afr_030_afr_gym_030_budget_request_validation(actors, club):
    """GYM-AFR-030 / AFR-GYM-030: negative amount and missing file are refused unchanged."""
    base = {"club_id": club.pk, "purpose": "Parts", "description": "Motors",
            "amount": "10.00", "document_url": DRIVE}
    head = actors.student(COORD)
    for invalid in ({**base, "amount": "-1.00"}, {**base, "document_url": ""}):
        response = head.post(f"{API}/budget-requests/create", invalid, format="json")
        assert response.status_code == 422
        assert not BudgetRequest.objects.exists()


def test_gym_afr_031_afr_gym_031_open_budget_request_tracking(actors, club):
    """GYM-AFR-031 / AFR-GYM-031: request remains open without review lifecycle."""
    response = actors.student(COORD).post(
        f"{API}/budget-requests/create",
        {"club_id": club.pk, "purpose": "Parts", "description": "Motors",
         "amount": "10.00", "document_url": DRIVE},
        format="json",
    )
    assert response.status_code == 201
    request = BudgetRequest.objects.get(pk=response.json()["id"])
    assert request.status == sm.OPEN
    assert not hasattr(request, "approved_at")


def test_gym_afr_032_afr_gym_032_event_report_submission(actors, club):
    """GYM-AFR-032 / AFR-GYM-032: event report and file are stored."""
    response = actors.student(COORD).post(
        f"{API}/event-reports/create", report_body(club.pk), format="json"
    )
    assert response.status_code == 201
    report = EventReport.objects.get(pk=response.json()["id"])
    assert (report.event_name, report.student_incharge_user_id, report.report_link) == (
        "RoboWars", MEMBER, DRIVE
    )


def test_gym_afr_033_afr_gym_033_required_event_report_file(actors, club):
    """GYM-AFR-033 / AFR-GYM-033: missing file is refused without storing report."""
    response = actors.student(COORD).post(
        f"{API}/event-reports/create", report_body(club.pk, report_url=""), format="json"
    )
    assert response.status_code == 422
    assert not EventReport.objects.exists()


def test_gym_afr_034_afr_gym_034_councillor_report_access_and_review(actors, club):
    """GYM-AFR-034 / AFR-GYM-034: assigned councillor can access and review report."""
    created = actors.student(COORD).post(
        f"{API}/event-reports/create", report_body(club.pk), format="json"
    )
    report_id = created.json()["id"]
    councillor = actors.faculty(COUNCILLOR)
    response = councillor.get(f"{API}/event-reports/{report_id}")
    assert response.status_code == 200
    assert response.json()["report_link"] == DRIVE
    assert not hasattr(EventReport.objects.get(pk=report_id), "status")
