"""Backend tests implementing the frozen BR-GYM design cases."""
from datetime import timedelta

import pytest
from django.utils import timezone

from fusion_auth.client import UserRef
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
    PollTarget,
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
    body = {"name": "BR Robotics", "category": "technical", "description": "Build robots.",
            "coordinator_user_id": COORD, "co_coordinator_user_id": CO_COORD,
            "faculty_councillor_user_id": COUNCILLOR}
    body.update(changes)
    return body


def budget_body(club_id, **changes):
    body = {"club_id": club_id, "purpose": "Parts", "description": "Motors",
            "amount": "10.00", "document_url": DRIVE}
    body.update(changes)
    return body


def report_body(club_id, **changes):
    body = {"club_id": club_id, "student_incharge_user_id": MEMBER,
            "event_name": "RoboWars", "event_at": (timezone.now() - timedelta(days=1)).isoformat(),
            "description": "Completed", "report_url": DRIVE}
    body.update(changes)
    return body


def create_poll(actors, club, **changes):
    response = actors.student(COORD).post(
        f"{API}/polls/create", poll_body(club.pk, **changes), format="json"
    )
    assert response.status_code == 201
    return response.json()


def test_br_gym_001_01_valid_student_leadership(actors):
    """BR-GYM-001-01; BR-GYM-001 valid student leadership."""
    response = actors.admin().post(f"{API}/clubs/create", club_body(), format="json")
    assert response.status_code == 201
    club = Club.objects.get(pk=response.json()["id"])
    assert sorted(club.leaders.values_list("user_id", flat=True)) == [COORD, CO_COORD]


def test_br_gym_001_02_invalid_student_leadership(actors):
    """BR-GYM-001-02; BR-GYM-001 invalid student leadership."""
    before = Club.objects.count()
    response = actors.admin().post(
        f"{API}/clubs/create", club_body(coordinator_user_id=COUNCILLOR), format="json"
    )
    assert response.status_code == 422
    assert Club.objects.count() == before


def test_br_gym_002_01_valid_faculty_councillor(actors):
    """BR-GYM-002-01; BR-GYM-002 valid faculty councillor."""
    response = actors.admin().post(f"{API}/clubs/create", club_body(), format="json")
    assert response.status_code == 201
    assert Club.objects.get(pk=response.json()["id"]).faculty_councillor_user_id == COUNCILLOR


def test_br_gym_002_02_invalid_faculty_councillor(actors):
    """BR-GYM-002-02; BR-GYM-002 invalid faculty councillor."""
    before = Club.objects.count()
    response = actors.admin().post(
        f"{API}/clubs/create", club_body(faculty_councillor_user_id=PLAIN), format="json"
    )
    assert response.status_code == 422
    assert Club.objects.count() == before


def test_br_gym_003_01_allowed_categories(actors):
    """BR-GYM-003-01; BR-GYM-003 allowed category."""
    for index, category in enumerate(("technical", "sports", "cultural")):
        body = club_body(name=f"BR Category {index}", category=category)
        response = actors.admin().post(f"{API}/clubs/create", body, format="json")
        assert response.status_code == 201
        assert Club.objects.get(pk=response.json()["id"]).category == category


def test_br_gym_003_02_disallowed_category(actors):
    """BR-GYM-003-02; BR-GYM-003 disallowed category."""
    before = Club.objects.count()
    response = actors.admin().post(
        f"{API}/clubs/create", club_body(category="literary"), format="json"
    )
    assert response.status_code == 422
    assert Club.objects.count() == before


def test_br_gym_004_01_creation_starts_open(actors):
    """BR-GYM-004-01; BR-GYM-004 creation transition."""
    response = actors.admin().post(f"{API}/clubs/create", club_body(), format="json")
    assert response.status_code == 201
    assert Club.objects.get(pk=response.json()["id"]).status == sm.OPEN


def test_br_gym_004_02_approval_confirms_open_club(actors):
    """BR-GYM-004-02; BR-GYM-004 approval transition."""
    club = make_club("BR Awaiting Approval", status=sm.OPEN)
    response = actors.admin().post(f"{API}/clubs/{club.pk}/approve")
    assert response.status_code == 200
    club.refresh_from_db()
    assert club.status == sm.CONFIRMED


def test_br_gym_005_01_valid_booking_time_range(actors, club, venues):
    """BR-GYM-005-01; BR-GYM-005 valid time range."""
    response = actors.student(COORD).post(
        f"{API}/sessions", session_body(club.pk, start="10:00", end="11:00"), format="json"
    )
    assert response.status_code == 201
    assert Booking.objects.get(pk=response.json()["id"]).start_time < Booking.objects.get(
        pk=response.json()["id"]
    ).end_time


def test_br_gym_005_02_invalid_booking_time_range(actors, club, venues):
    """BR-GYM-005-02; BR-GYM-005 invalid time range."""
    before = Booking.objects.count()
    for start, end in (("10:00", "10:00"), ("11:00", "10:00")):
        response = actors.student(COORD).post(
            f"{API}/sessions", session_body(club.pk, start=start, end=end), format="json"
        )
        assert response.status_code == 422
        assert Booking.objects.count() == before


def test_br_gym_006_01_non_overlapping_booking(actors, club, venues):
    """BR-GYM-006-01; BR-GYM-006 no overlap."""
    head = actors.student(COORD)
    assert head.post(f"{API}/sessions", session_body(club.pk), format="json").status_code == 201
    response = head.post(
        f"{API}/sessions", session_body(club.pk, start="11:00", end="12:00"), format="json"
    )
    assert response.status_code == 201
    assert Booking.objects.count() == 2


def _overlap(actors, club, venues, first_kind, second_kind):
    head = actors.student(COORD)
    first_path = "sessions" if first_kind == "session" else "events"
    second_path = "sessions" if second_kind == "session" else "events"
    first_body = session_body(club.pk) if first_kind == "session" else event_body(club.pk)
    second_body = (session_body(club.pk, start="10:30", end="11:30")
                   if second_kind == "session"
                   else event_body(club.pk, start="10:30", end="11:30"))
    assert head.post(f"{API}/{first_path}", first_body, format="json").status_code == 201
    before = Booking.objects.count()
    response = head.post(f"{API}/{second_path}", second_body, format="json")
    assert response.status_code == 409
    assert Booking.objects.count() == before


def test_br_gym_006_02_session_session_overlap(actors, club, venues):
    """BR-GYM-006-02; BR-GYM-006 session-session overlap."""
    _overlap(actors, club, venues, "session", "session")


def test_br_gym_006_03_event_event_overlap(actors, club, venues):
    """BR-GYM-006-03; BR-GYM-006 event-event overlap."""
    _overlap(actors, club, venues, "event", "event")


def test_br_gym_006_04_session_event_overlap(actors, club, venues):
    """BR-GYM-006-04; BR-GYM-006 session-event overlap."""
    _overlap(actors, club, venues, "session", "event")


def test_br_gym_006_05_event_session_overlap(actors, club, venues):
    """BR-GYM-006-05; BR-GYM-006 event-session overlap."""
    _overlap(actors, club, venues, "event", "session")


def test_br_gym_007_01_apply_to_confirmed_club(actors, club):
    """BR-GYM-007-01; BR-GYM-007 confirmed club eligibility."""
    response = actors.student(PLAIN).post(
        f"{API}/memberships/apply", {"club_id": club.pk, "description": "Interested"},
        format="json",
    )
    assert response.status_code == 201
    assert Membership.objects.get(pk=response.json()["id"]).status == sm.OPEN


def test_br_gym_007_02_open_club_application_refused(actors):
    """BR-GYM-007-02; BR-GYM-007 non-confirmed club eligibility."""
    club = make_club("BR Open", status=sm.OPEN)
    before = Membership.objects.count()
    response = actors.student(PLAIN).post(
        f"{API}/memberships/apply", {"club_id": club.pk, "description": "Interested"},
        format="json",
    )
    assert response.status_code == 422
    assert Membership.objects.count() == before


def test_br_gym_008_01_application_to_different_club(actors, club, other_club):
    """BR-GYM-008-01; BR-GYM-008 different-club application."""
    join(club, PLAIN, status=sm.OPEN)
    response = actors.student(PLAIN).post(
        f"{API}/memberships/apply", {"club_id": other_club.pk, "description": "Also interested"},
        format="json",
    )
    assert response.status_code == 201
    assert Membership.objects.filter(user_id=PLAIN).count() == 2


def test_br_gym_009_01_duplicate_application_unchanged(actors, club):
    """BR-GYM-009-01; BR-GYM-009 duplicate same-club application."""
    original = join(club, PLAIN, status=sm.OPEN)
    before = list(Membership.objects.filter(user_id=PLAIN).values_list("pk", "status", "description"))
    response = actors.student(PLAIN).post(
        f"{API}/memberships/apply", {"club_id": club.pk, "description": "Duplicate"}, format="json"
    )
    assert response.status_code == 409
    assert list(Membership.objects.filter(user_id=PLAIN).values_list("pk", "status", "description")) == before
    assert Membership.objects.get(pk=original.pk).description == "x"


def _head_operation(actors, actor_id, club):
    return actors.student(actor_id).post(
        f"{API}/clubs/{club.pk}/leadership",
        {"coordinator_user_id": MEMBER, "co_coordinator_user_id": PLAIN}, format="json",
    )


def test_br_gym_010_01_coordinator_authorized(actors, club):
    """BR-GYM-010-01; BR-GYM-010 coordinator authorization."""
    response = _head_operation(actors, COORD, club)
    assert response.status_code == 200
    assert response.json() == {"coordinator": MEMBER, "co_coordinator": PLAIN}


def test_br_gym_010_02_cocoordinator_authorized(actors, club):
    """BR-GYM-010-02; BR-GYM-010 co-coordinator authorization."""
    response = _head_operation(actors, CO_COORD, club)
    assert response.status_code == 200
    assert response.json() == {"coordinator": MEMBER, "co_coordinator": PLAIN}


def test_br_gym_010_03_non_head_refused(actors, club):
    """BR-GYM-010-03; BR-GYM-010 non-Club Head authorization."""
    before = list(LeadershipAssignment.objects.filter(club=club, valid_to__isnull=True)
                  .values_list("user_id", "role"))
    response = _head_operation(actors, PLAIN, club)
    assert response.status_code == 403
    assert list(LeadershipAssignment.objects.filter(club=club, valid_to__isnull=True)
                .values_list("user_id", "role")) == before


def test_br_gym_011_01_approve_membership_with_remarks(actors, club):
    """BR-GYM-011-01; BR-GYM-011 approval transition with remarks."""
    application = join(club, PLAIN, status=sm.OPEN)
    response = actors.student(COORD).post(
        f"{API}/memberships/approve", {"ids": [application.pk], "remarks": "Welcome"}, format="json"
    )
    assert response.status_code == 200
    application.refresh_from_db()
    assert application.status == sm.CONFIRMED and application.remarks == "Welcome"


def test_br_gym_011_02_approve_membership_without_remarks(actors, club):
    """BR-GYM-011-02; BR-GYM-011 approval transition without remarks."""
    application = join(club, PLAIN, status=sm.OPEN)
    response = actors.student(COORD).post(
        f"{API}/memberships/approve", {"ids": [application.pk]}, format="json"
    )
    assert response.status_code == 200
    application.refresh_from_db()
    assert application.status == sm.CONFIRMED


def test_br_gym_012_01_poll_with_two_choices(actors, club):
    """BR-GYM-012-01; BR-GYM-012 minimum choice threshold met."""
    response = actors.student(COORD).post(
        f"{API}/polls/create", poll_body(club.pk, choices=["One", "Two"]), format="json"
    )
    assert response.status_code == 201
    assert Poll.objects.get(pk=response.json()["id"]).choices.count() == 2


def test_br_gym_012_02_poll_fewer_than_two_choices_refused(actors, club):
    """BR-GYM-012-02; BR-GYM-012 minimum choice threshold unmet."""
    before = Poll.objects.count()
    response = actors.student(COORD).post(
        f"{API}/polls/create", poll_body(club.pk, choices=["Only"]), format="json"
    )
    assert response.status_code == 422
    assert Poll.objects.count() == before


def test_br_gym_013_01_poll_batch_branch_targeting(actors, club):
    """BR-GYM-013-01; BR-GYM-013 selected batch and branch targeting."""
    created = create_poll(actors, club, targets=[{"batch_year": 2023, "discipline": "CSE"}])
    target = PollTarget.objects.get(poll_id=created["id"])
    assert (target.batch_year, target.discipline) == (2023, "CSE")
    included = actors.student(PLAIN).get(f"{API}/polls").json()["results"]
    excluded = actors.student(1010).get(f"{API}/polls").json()["results"]
    assert [p["id"] for p in included] == [created["id"]]
    assert created["id"] not in [p["id"] for p in excluded]
    notice = NotificationOutbox.objects.get(is_broadcast=True)
    assert notice.payload["poll_id"] == created["id"]


def test_br_gym_013_02_all_branches_target(actors, club):
    """BR-GYM-013-02; BR-GYM-013 all-branches selection exception."""
    actors.users[1012] = UserRef(
        user_id=1012, username="stu1012", display_name="Student 1012", kind="student",
        discipline="ECE", batch_year=2023, email="stu1012@example.invalid",
    )
    created = create_poll(actors, club, targets=[{"batch_year": 2023, "discipline": ""}])
    target = PollTarget.objects.get(poll_id=created["id"])
    assert (target.batch_year, target.discipline) == (2023, "")
    assert created["id"] in [p["id"] for p in actors.student(PLAIN).get(f"{API}/polls").json()["results"]]
    branch_student = actors.student(1012)
    assert created["id"] in [
        poll["id"] for poll in branch_student.get(f"{API}/polls").json()["results"]
    ]


def test_br_gym_014_01_active_unexpired_poll_access(actors, club):
    """BR-GYM-014-01; BR-GYM-014 active unexpired eligible poll."""
    created = create_poll(actors, club)
    response = actors.student(PLAIN).get(f"{API}/polls")
    assert response.status_code == 200
    assert created["id"] in [p["id"] for p in response.json()["results"]]


def test_br_gym_014_02_inactive_poll_participation():
    """BR-GYM-014-02; no inactive state exists in the poll model or API."""
    pytest.skip("NOT_AUTOMATED: frozen A8_BASE has no inactive poll state or interface.")


def test_br_gym_014_03_expired_poll_participation(actors, club):
    """BR-GYM-014-03; BR-GYM-014 expired poll."""
    created = create_poll(actors, club, expires_on=(timezone.localdate() - timedelta(days=1)).isoformat())
    response = actors.student(PLAIN).post(
        f"{API}/polls/{created['id']}/votes", {"choice_id": created["choices"][0]["id"]},
        format="json",
    )
    assert response.status_code == 404
    assert not Vote.objects.filter(poll_id=created["id"]).exists()


def test_br_gym_014_04_outside_target_poll_participation(actors, club):
    """BR-GYM-014-04; BR-GYM-014 student outside target audience."""
    created = create_poll(actors, club)
    before = Vote.objects.count()
    outsider = actors.student(1010)
    assert created["id"] not in [p["id"] for p in outsider.get(f"{API}/polls").json()["results"]]
    response = outsider.post(
        f"{API}/polls/{created['id']}/votes", {"choice_id": created["choices"][0]["id"]},
        format="json",
    )
    assert response.status_code == 404
    assert Vote.objects.count() == before


def test_br_gym_015_01_first_poll_vote(actors, club):
    """BR-GYM-015-01; BR-GYM-015 first vote."""
    created = create_poll(actors, club)
    response = actors.student(PLAIN).post(
        f"{API}/polls/{created['id']}/votes", {"choice_id": created["choices"][0]["id"]},
        format="json",
    )
    assert response.status_code == 201
    assert Vote.objects.filter(poll_id=created["id"], user_id=PLAIN).count() == 1


def test_br_gym_015_02_second_poll_vote_refused(actors, club):
    """BR-GYM-015-02; BR-GYM-015 second vote."""
    created = create_poll(actors, club)
    voter = actors.student(PLAIN)
    first, second = [choice["id"] for choice in created["choices"]]
    assert voter.post(f"{API}/polls/{created['id']}/votes", {"choice_id": first}, format="json").status_code == 201
    before = list(Vote.objects.filter(poll_id=created["id"]).values_list("user_id", "choice_id"))
    response = voter.post(f"{API}/polls/{created['id']}/votes", {"choice_id": second}, format="json")
    assert response.status_code == 409
    assert list(Vote.objects.filter(poll_id=created["id"]).values_list("user_id", "choice_id")) == before


def test_br_gym_016_01_leadership_succession(actors, club):
    """BR-GYM-016-01; BR-GYM-016 leadership succession."""
    response = actors.student(COORD).post(
        f"{API}/clubs/{club.pk}/leadership",
        {"coordinator_user_id": MEMBER, "co_coordinator_user_id": PLAIN}, format="json",
    )
    assert response.status_code == 200
    assert sorted(LeadershipAssignment.objects.filter(club=club, valid_to__isnull=True)
                  .values_list("user_id", flat=True)) == [MEMBER, PLAIN]
    assert LeadershipAssignment.objects.filter(club=club, valid_to__isnull=False).count() == 2


def test_br_gym_017_01_zero_budget_amount(actors, club):
    """BR-GYM-017-01; BR-GYM-017 zero budget boundary."""
    response = actors.student(COORD).post(
        f"{API}/budget-requests/create", budget_body(club.pk, amount="0"), format="json"
    )
    assert response.status_code == 201
    assert BudgetRequest.objects.get(pk=response.json()["id"]).amount == 0


def test_br_gym_017_02_positive_budget_amount(actors, club):
    """BR-GYM-017-02; BR-GYM-017 positive budget."""
    response = actors.student(COORD).post(
        f"{API}/budget-requests/create", budget_body(club.pk, amount="25.00"), format="json"
    )
    assert response.status_code == 201
    assert BudgetRequest.objects.get(pk=response.json()["id"]).amount == 25


def test_br_gym_017_03_negative_budget_refused(actors, club):
    """BR-GYM-017-03; BR-GYM-017 negative budget."""
    before = BudgetRequest.objects.count()
    response = actors.student(COORD).post(
        f"{API}/budget-requests/create", budget_body(club.pk, amount="-1"), format="json"
    )
    assert response.status_code == 422
    assert BudgetRequest.objects.count() == before


def test_br_gym_018_01_supporting_file_present(actors, club):
    """BR-GYM-018-01; BR-GYM-018 supporting file present."""
    response = actors.student(COORD).post(
        f"{API}/budget-requests/create", budget_body(club.pk), format="json"
    )
    assert response.status_code == 201
    assert BudgetRequest.objects.get(pk=response.json()["id"]).document_link == DRIVE


def test_br_gym_018_02_supporting_file_missing_refused(actors, club):
    """BR-GYM-018-02; BR-GYM-018 supporting file missing."""
    before = BudgetRequest.objects.count()
    response = actors.student(COORD).post(
        f"{API}/budget-requests/create", budget_body(club.pk, document_url=""), format="json"
    )
    assert response.status_code == 422
    assert BudgetRequest.objects.count() == before


def test_br_gym_019_01_report_file_present(actors, club):
    """BR-GYM-019-01; BR-GYM-019 report file present."""
    response = actors.student(COORD).post(
        f"{API}/event-reports/create", report_body(club.pk), format="json"
    )
    assert response.status_code == 201
    assert EventReport.objects.get(pk=response.json()["id"]).report_link == DRIVE


def test_br_gym_019_02_report_file_missing_refused(actors, club):
    """BR-GYM-019-02; BR-GYM-019 report file missing."""
    before = EventReport.objects.count()
    response = actors.student(COORD).post(
        f"{API}/event-reports/create", report_body(club.pk, report_url=""), format="json"
    )
    assert response.status_code == 422
    assert EventReport.objects.count() == before


def test_br_gym_020_01_configured_venue(actors, club, venues):
    """BR-GYM-020-01; BR-GYM-020 configured venue."""
    response = actors.student(COORD).post(
        f"{API}/sessions", session_body(club.pk, venue="LHTC 101"), format="json"
    )
    assert response.status_code == 201
    assert Booking.objects.get(pk=response.json()["id"]).venue_name == "LHTC 101"


def test_br_gym_020_02_unconfigured_venue_refused(actors, club, venues):
    """BR-GYM-020-02; BR-GYM-020 unconfigured venue."""
    before = Booking.objects.count()
    response = actors.student(COORD).post(
        f"{API}/sessions", session_body(club.pk, venue="Basement"), format="json"
    )
    assert response.status_code == 422
    assert Booking.objects.count() == before


def test_br_gym_021_01_assigned_councillor_report_access(actors, club):
    """BR-GYM-021-01; BR-GYM-021 assigned councillor access."""
    created = actors.student(COORD).post(
        f"{API}/event-reports/create", report_body(club.pk), format="json"
    )
    report_id = created.json()["id"]
    response = actors.faculty(COUNCILLOR).get(f"{API}/event-reports/{report_id}")
    assert response.status_code == 200
    assert response.json()["id"] == report_id


def test_br_gym_021_02_unassigned_faculty_report_refused(actors, club):
    """BR-GYM-021-02; BR-GYM-021 unassigned faculty access."""
    created = actors.student(COORD).post(
        f"{API}/event-reports/create", report_body(club.pk), format="json"
    )
    before = EventReport.objects.count()
    response = actors.faculty(OTHER_FACULTY).get(f"{API}/event-reports/{created.json()['id']}")
    assert response.status_code == 404
    assert EventReport.objects.count() == before
