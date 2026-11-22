"""Each live use case, end to end through HTTP, as each actor in turn."""
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.gymkhana.domain import state_machine as sm
from modules.gymkhana.models import (
    AuditEvent,
    Booking,
    BudgetRequest,
    Club,
    EventReport,
    LeadershipAssignment,
    Membership,
    NotificationOutbox,
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
    poll_body,
    session_body,
)

pytestmark = pytest.mark.django_db
API = "/api/v1/gymkhana"


def club_body(**kw):
    body = {"name": "Robotics", "category": "technical", "description": "Builds robots.",
            "coordinator_user_id": COORD, "co_coordinator_user_id": CO_COORD,
            "faculty_councillor_user_id": COUNCILLOR}
    body.update(kw)
    return body


# -- BW-GYM-03 -----------------------------------------------------------------
def test_uc_gym_001_and_011_student_admin_creates_then_confirms_a_club(actors):
    """BW-GYM-03, CFR-GYM-001, AFR-GYM-001, AFR-GYM-005, AFR-GYM-006."""
    admin = actors.admin()
    r = admin.post(f"{API}/clubs/create", club_body(), format="json")
    assert r.status_code == 201, r.content
    body = r.json()
    assert body["status"] == "open"
    assert body["leaders"] == {"coordinator": COORD, "co_coordinator": CO_COORD}
    # People are shown by name, not by an id nobody can act on.
    assert body["leader_names"] == {"coordinator": f"Student {COORD} (stu{COORD})",
                                    "co_coordinator": f"Student {CO_COORD} (stu{CO_COORD})"}
    assert body["councillor_name"] == f"Faculty {COUNCILLOR} (fac{COUNCILLOR})"

    r = admin.post(f"{API}/clubs/{body['id']}/approve")
    assert r.status_code == 200 and r.json()["status"] == "confirmed"
    club = Club.objects.get(pk=body["id"])
    assert club.approved_by_user_id == 9001 and club.approved_at is not None
    assert list(AuditEvent.objects.filter(object_id=club.pk, object_type="club")
                .values_list("action", flat=True)) == ["club.created", "club.approved"]


def test_uc_gym_001_alternative_flow_names_every_invalid_assignment(actors):
    """BR-GYM-001, BR-GYM-002, AFR-GYM-002, AFR-GYM-003: no club is created."""
    r = actors.admin().post(f"{API}/clubs/create",
                            club_body(coordinator_user_id=COUNCILLOR,
                                      co_coordinator_user_id=777777,
                                      faculty_councillor_user_id=PLAIN), format="json")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_assignment"
    fields = {d["field"] for d in r.json()["error"]["details"]}
    assert fields == {"coordinator_user_id", "co_coordinator_user_id",
                      "faculty_councillor_user_id"}
    assert not Club.objects.exists()


def test_uc_gym_001_category_outside_the_three_is_refused(actors):
    """BR-GYM-003, AFR-GYM-004."""
    r = actors.admin().post(f"{API}/clubs/create", club_body(category="Literary"),
                            format="json")
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_category"
    assert not Club.objects.exists()


def test_uc_gym_001_same_student_cannot_hold_both_seats(actors):
    r = actors.admin().post(f"{API}/clubs/create", club_body(co_coordinator_user_id=COORD),
                            format="json")
    assert r.status_code == 422 and r.json()["error"]["code"] == "same_leader_twice"


def test_uc_gym_001_club_names_are_unique_ignoring_case(actors, club):
    r = actors.admin().post(f"{API}/clubs/create", club_body(name="ROBOTICS"),
                            format="json")
    assert r.status_code == 409 and r.json()["error"]["code"] == "club_name_taken"


def test_uc_gym_001_missing_name_or_description_is_refused(actors):
    admin = actors.admin()
    assert admin.post(f"{API}/clubs/create", club_body(name=" "),
                      format="json").json()["error"]["code"] == "missing_field"
    assert admin.post(f"{API}/clubs/create", club_body(description=""),
                      format="json").status_code == 422


def test_uc_gym_011_exception_flow_a_confirmed_club_is_not_approved_again(actors, club):
    """BR-GYM-004: no transition out of confirmed."""
    r = actors.admin().post(f"{API}/clubs/{club.pk}/approve")
    assert r.status_code == 409 and r.json()["error"]["code"] == "club_already_confirmed"


def test_uc_gym_011_unknown_club_is_404(actors):
    assert actors.admin().post(f"{API}/clubs/999999/approve").status_code == 404


def test_student_admin_lists_open_clubs_and_a_student_does_not(actors):
    from modules.gymkhana.tests.conftest import make_club
    make_club("Pending", status=sm.OPEN, coord=1005, co=1006)
    make_club("Live")
    admin_names = {c["name"] for c in actors.admin().get(f"{API}/clubs").json()["results"]}
    student_names = {c["name"] for c in
                     actors.student(PLAIN).get(f"{API}/clubs").json()["results"]}
    assert admin_names == {"Pending", "Live"}
    assert student_names == {"Live"}
    assert {c["name"] for c in actors.admin().get(
        f"{API}/clubs?status=open&category=technical").json()["results"]} == {"Pending"}


# -- BW-GYM-01 -----------------------------------------------------------------
def test_uc_gym_004_and_005_student_applies_and_club_head_approves(actors, club):
    """BW-GYM-01, CFR-GYM-004, AFR-GYM-016, AFR-GYM-019, AFR-GYM-020, AFR-GYM-021, AFR-GYM-022."""
    # BR-GYM-011: approval moves open to confirmed and keeps the remarks.
    r = actors.student(PLAIN).post(f"{API}/memberships/apply",
                                   {"club_id": club.pk, "description": "I build drones."},
                                   format="json")
    assert r.status_code == 201 and r.json()["status"] == "open"
    mid = r.json()["id"]

    head = actors.student(COORD)
    pending = head.get(f"{API}/memberships?club={club.pk}&status=open").json()["results"]
    assert [m["id"] for m in pending] == [mid]
    assert pending[0]["applicant_name"] == f"Student {PLAIN} (stu{PLAIN})"
    r = head.post(f"{API}/memberships/approve", {"ids": [mid], "remarks": "Welcome"},
                  format="json")
    assert r.status_code == 200 and r.json()[0]["outcome"] == "approved"

    m = Membership.objects.get(pk=mid)
    assert (m.status, m.remarks, m.approved_by_user_id) == ("confirmed", "Welcome", COORD)
    mine = actors.student(PLAIN).get(f"{API}/memberships").json()["results"]
    assert mine[0]["status"] == "confirmed"


def test_uc_gym_004_alternative_flow_other_clubs_remain_open(actors, club, other_club):
    """BR-GYM-008, AFR-GYM-017."""
    student = actors.student(PLAIN)
    for c in (club, other_club):
        assert student.post(f"{API}/memberships/apply",
                            {"club_id": c.pk, "description": "x"},
                            format="json").status_code == 201
    assert Membership.objects.filter(user_id=PLAIN).count() == 2


def test_uc_gym_004_exception_flow_duplicate_is_refused_and_original_kept(actors, club):
    """BR-GYM-009, AFR-GYM-018."""
    student = actors.student(PLAIN)
    student.post(f"{API}/memberships/apply", {"club_id": club.pk, "description": "first"},
                 format="json")
    r = student.post(f"{API}/memberships/apply", {"club_id": club.pk, "description": "2nd"},
                     format="json")
    assert r.status_code == 409 and r.json()["error"]["code"] == "duplicate_application"
    assert Membership.objects.get(user_id=PLAIN).description == "first"


def test_uc_gym_004_an_open_club_cannot_be_applied_to(actors):
    """BR-GYM-007."""
    from modules.gymkhana.tests.conftest import make_club
    pending = make_club("Pending", status=sm.OPEN)
    r = actors.student(PLAIN).post(f"{API}/memberships/apply",
                                   {"club_id": pending.pk, "description": "x"},
                                   format="json")
    assert r.status_code == 404
    assert not Membership.objects.exists()


def test_uc_gym_004_needs_a_description(actors, club):
    r = actors.student(PLAIN).post(f"{API}/memberships/apply",
                                   {"club_id": club.pk, "description": " "}, format="json")
    assert r.status_code == 422


def test_uc_gym_005_alternative_flow_each_selected_application_is_independent(
        actors, club, other_club):
    """UC-GYM-005 exception flow: a foreign or already-confirmed one is left unchanged."""
    open_one = join(club, PLAIN, status=sm.OPEN)
    done = join(club, MEMBER, status=sm.CONFIRMED)
    foreign = join(other_club, PLAIN, status=sm.OPEN)
    r = actors.student(COORD).post(f"{API}/memberships/approve",
                                   {"ids": [open_one.pk, done.pk, foreign.pk, open_one.pk]},
                                   format="json")
    outcomes = {o["id"]: o["code"] for o in r.json()}
    assert outcomes == {open_one.pk: "approved", done.pk: "already_confirmed",
                        foreign.pk: "not_found"}
    foreign.refresh_from_db()
    assert foreign.status == "open"


def test_uc_gym_005_a_club_head_cannot_approve_their_own_application(actors, club):
    mine = join(club, COORD, status=sm.OPEN)
    r = actors.student(COORD).post(f"{API}/memberships/approve", {"ids": [mine.pk]},
                                   format="json")
    assert r.json()[0]["code"] == "self_approval"
    r = actors.student(CO_COORD).post(f"{API}/memberships/approve", {"ids": [mine.pk]},
                                      format="json")
    assert r.json()[0]["code"] == "approved"


def test_uc_gym_005_input_bounds(actors, club):
    head = actors.student(COORD)
    assert head.post(f"{API}/memberships/approve", {"ids": []},
                     format="json").status_code == 400
    assert head.post(f"{API}/memberships/approve",
                     {"ids": [1], "remarks": "x" * 1001}, format="json").status_code == 400


# -- Bookings ------------------------------------------------------------------
def test_uc_gym_002_club_head_books_a_session_and_members_are_notified(
        actors, club, venues):
    """CFR-GYM-003, AFR-GYM-010, AFR-GYM-013, BR-GYM-010, BR-GYM-020."""
    join(club, MEMBER)
    join(club, PLAIN, status=sm.OPEN)
    r = actors.student(COORD).post(f"{API}/sessions", session_body(club.pk), format="json")
    assert r.status_code == 201, r.content
    assert r.json()["kind"] == "session" and r.json()["poster_link"] == ""
    rows = NotificationOutbox.objects.filter(topic="session.booked")
    assert list(rows.values_list("recipient_user_id", flat=True)) == [MEMBER]

    seen = actors.student(MEMBER).get(f"{API}/bookings").json()["results"]
    assert [b["id"] for b in seen] == [r.json()["id"]]
    assert actors.student(PLAIN).get(f"{API}/bookings").json()["results"] == []


def test_uc_gym_002_alternative_flow_overlapping_slot_is_rejected(actors, club, venues):
    """BR-GYM-006, AFR-GYM-012: session-session overlap."""
    head = actors.student(COORD)
    head.post(f"{API}/sessions", session_body(club.pk), format="json")
    r = head.post(f"{API}/sessions", session_body(club.pk, start="10:30", end="11:30"),
                  format="json")
    assert r.status_code == 409 and r.json()["error"]["code"] == "venue_slot_taken"
    assert head.post(f"{API}/sessions", session_body(club.pk, start="11:00", end="12:00"),
                     format="json").status_code == 201
    assert head.post(f"{API}/sessions",
                     session_body(club.pk, start="10:30", end="11:30",
                                  venue="Open Air Theatre"),
                     format="json").status_code == 201


def test_uc_gym_002_exception_flows_invalid_venue_or_time_book_nothing(actors, club, venues):
    """BR-GYM-005, BR-GYM-020, AFR-GYM-011."""
    head = actors.student(COORD)
    r = head.post(f"{API}/sessions", session_body(club.pk, venue="Basement"), format="json")
    assert r.status_code == 422 and r.json()["error"]["code"] == "unknown_venue"
    r = head.post(f"{API}/sessions", session_body(club.pk, start="11:00", end="10:00"),
                  format="json")
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_time_range"
    past = (timezone.localdate() - timedelta(days=1)).isoformat()
    r = head.post(f"{API}/sessions", session_body(club.pk, day=past), format="json")
    assert r.status_code == 409 and r.json()["error"]["code"] == "booking_in_past"
    assert not Booking.objects.exists()


def test_uc_gym_002_venue_matches_ignoring_case_and_stores_the_canonical_name(
        actors, club, venues):
    r = actors.student(COORD).post(f"{API}/sessions",
                                   session_body(club.pk, venue="lhtc 101"), format="json")
    assert r.json()["venue_name"] == "LHTC 101"


def test_uc_gym_003_club_head_books_an_event_with_the_clubs_councillor(actors, club, venues):
    """AFR-GYM-014, AFR-GYM-015, BR-GYM-002."""
    join(club, MEMBER)
    r = actors.student(COORD).post(f"{API}/events", event_body(club.pk), format="json")
    assert r.status_code == 201, r.content
    assert r.json()["faculty_user_id"] == COUNCILLOR
    assert r.json()["poster_link"] == DRIVE
    assert NotificationOutbox.objects.filter(topic="event.booked",
                                             recipient_user_id=MEMBER).exists()


def test_uc_gym_003_alternative_flow_session_event_overlap_is_rejected(actors, club, venues):
    """BR-GYM-006: cross-type, in both orders."""
    head = actors.student(COORD)
    head.post(f"{API}/sessions", session_body(club.pk), format="json")
    r = head.post(f"{API}/events", event_body(club.pk, start="10:30", end="12:00"),
                  format="json")
    assert r.status_code == 409
    head.post(f"{API}/events", event_body(club.pk, start="14:00", end="15:00"),
              format="json")
    r = head.post(f"{API}/sessions", session_body(club.pk, start="14:30", end="16:00"),
                  format="json")
    assert r.status_code == 409
    r = head.post(f"{API}/events", event_body(club.pk, start="14:00", end="15:00"),
                  format="json")
    assert r.status_code == 409, "event-event overlap"


def test_uc_gym_003_exception_flows(actors, club, venues):
    """Poster required for events; a councillor no longer faculty blocks the event."""
    head = actors.student(COORD)
    r = head.post(f"{API}/events", {**event_body(club.pk), "poster_url": ""}, format="json")
    assert r.json()["error"]["code"] == "poster_required"
    r = head.post(f"{API}/events", {**event_body(club.pk), "poster_url": "https://evil.test/x"},
                  format="json")
    assert r.json()["error"]["code"] == "url_not_drive"
    r = head.post(f"{API}/events", {**event_body(club.pk), "event_name": ""}, format="json")
    assert r.status_code == 422
    Club.objects.filter(pk=club.pk).update(faculty_councillor_user_id=PLAIN)
    r = head.post(f"{API}/events", event_body(club.pk), format="json")
    assert r.status_code == 409 and r.json()["error"]["code"] == "councillor_invalid"
    assert not Booking.objects.exists()


def test_booking_with_no_venue_list_says_what_is_missing(actors, club):
    r = actors.student(COORD).post(f"{API}/sessions", session_body(club.pk), format="json")
    assert r.status_code == 409 and r.json()["error"]["code"] == "no_venues_configured"


def test_venue_list_is_the_one_in_effect(actors, club, venues):
    assert actors.student(COORD).get(f"{API}/venues").json() == {
        "venues": ["LHTC 101", "Open Air Theatre"]}


# -- BW-GYM-02 -----------------------------------------------------------------
def test_uc_gym_006_and_007_poll_created_notified_and_voted_once(actors, club):
    """BW-GYM-02, CFR-GYM-005, AFR-GYM-023, AFR-GYM-025, AFR-GYM-026, AFR-GYM-027, AFR-GYM-028."""
    r = actors.student(COORD).post(f"{API}/polls/create", poll_body(club.pk), format="json")
    assert r.status_code == 201, r.content
    poll = r.json()
    assert NotificationOutbox.objects.get(is_broadcast=True).payload["poll_id"] == poll["id"]

    voter = actors.student(PLAIN)
    open_polls = voter.get(f"{API}/polls").json()["results"]
    assert [p["id"] for p in open_polls] == [poll["id"]]
    assert open_polls[0]["my_choice_id"] is None
    choice = poll["choices"][0]["id"]
    assert voter.post(f"{API}/polls/{poll['id']}/votes", {"choice_id": choice},
                      format="json").status_code == 201
    assert voter.get(f"{API}/polls").json()["results"][0]["my_choice_id"] == choice

    managed = actors.student(COORD).get(f"{API}/polls/managed").json()["results"][0]
    assert managed["total_votes"] == 1
    assert {c["label"]: c["votes"] for c in managed["choices"]} == {"Drones": 1, "ROS": 0}


def test_uc_gym_007_exception_flow_second_vote_is_rejected(actors, club):
    """BR-GYM-015: tally unchanged."""
    poll = actors.student(COORD).post(f"{API}/polls/create", poll_body(club.pk),
                                      format="json").json()
    voter = actors.student(PLAIN)
    a, b = (c["id"] for c in poll["choices"])
    voter.post(f"{API}/polls/{poll['id']}/votes", {"choice_id": a}, format="json")
    r = voter.post(f"{API}/polls/{poll['id']}/votes", {"choice_id": b}, format="json")
    assert r.status_code == 409 and r.json()["error"]["code"] == "already_voted"
    assert list(Vote.objects.values_list("choice_id", flat=True)) == [a]


def test_uc_gym_007_exception_flow_untargeted_student_cannot_see_or_vote(actors, club):
    """BR-GYM-013, BR-GYM-014: ECE 2024 and a student with no batch on record."""
    poll = actors.student(COORD).post(f"{API}/polls/create", poll_body(club.pk),
                                      format="json").json()
    for uid in (1010, 1011):
        outsider = actors.student(uid)
        assert outsider.get(f"{API}/polls").json()["results"] == []
        r = outsider.post(f"{API}/polls/{poll['id']}/votes",
                          {"choice_id": poll["choices"][0]["id"]}, format="json")
        assert r.status_code == 404
    assert not Vote.objects.exists()


def test_uc_gym_006_alternative_flow_all_branches_of_a_batch(actors, club):
    body = poll_body(club.pk, targets=[{"batch_year": 2024, "discipline": ""}])
    poll = actors.student(COORD).post(f"{API}/polls/create", body, format="json").json()
    assert [p["id"] for p in actors.student(1010).get(f"{API}/polls").json()["results"]] \
        == [poll["id"]]


def test_uc_gym_007_exception_flow_expired_poll_takes_no_vote(actors, club):
    """BR-GYM-014."""
    from modules.gymkhana.models import Poll
    poll = actors.student(COORD).post(f"{API}/polls/create", poll_body(club.pk),
                                      format="json").json()
    Poll.objects.filter(pk=poll["id"]).update(
        expires_on=timezone.localdate() - timedelta(days=1))
    voter = actors.student(PLAIN)
    assert voter.get(f"{API}/polls").json()["results"] == []
    r = voter.post(f"{API}/polls/{poll['id']}/votes",
                   {"choice_id": poll["choices"][0]["id"]}, format="json")
    assert r.status_code == 409 and r.json()["error"]["code"] == "poll_closed"


def test_uc_gym_007_a_choice_from_another_poll_is_refused(actors, club):
    head = actors.student(COORD)
    p1 = head.post(f"{API}/polls/create", poll_body(club.pk), format="json").json()
    p2 = head.post(f"{API}/polls/create", poll_body(club.pk, title="Other"),
                   format="json").json()
    r = actors.student(PLAIN).post(f"{API}/polls/{p1['id']}/votes",
                                   {"choice_id": p2["choices"][0]["id"]}, format="json")
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_choice"


def test_uc_gym_006_exception_flow_invalid_poll_is_not_created(actors, club):
    """BR-GYM-012, AFR-GYM-024."""
    head = actors.student(COORD)
    for body, err in (
            (poll_body(club.pk, choices=["Only"]), "too_few_choices"),
            (poll_body(club.pk, targets=[]), "no_targets"),
            (poll_body(club.pk, targets=[{"batch_year": 1900}]), "invalid_target"),
            (poll_body(club.pk, expires_on=(timezone.localdate()
                                            - timedelta(days=1)).isoformat()),
             "expiry_in_past"),
            (poll_body(club.pk, title=" "), "missing_field")):
        r = head.post(f"{API}/polls/create", body, format="json")
        assert r.status_code == 422 and r.json()["error"]["code"] == err, body
    from modules.gymkhana.models import Poll
    assert not Poll.objects.exists()
    assert not NotificationOutbox.objects.exists()


# -- Leadership ----------------------------------------------------------------
def test_uc_gym_008_club_head_replaces_both_leaders(actors, club):
    """CFR-GYM-002, AFR-GYM-007, AFR-GYM-008, AFR-GYM-009, BR-GYM-016."""
    r = actors.student(COORD).post(f"{API}/clubs/{club.pk}/leadership",
                                   {"coordinator_user_id": MEMBER,
                                    "co_coordinator_user_id": PLAIN}, format="json")
    assert r.status_code == 200 and r.json() == {"coordinator": MEMBER,
                                                 "co_coordinator": PLAIN}
    current = LeadershipAssignment.objects.filter(club=club, valid_to__isnull=True)
    assert sorted(current.values_list("user_id", flat=True)) == [MEMBER, PLAIN]
    ended = LeadershipAssignment.objects.filter(club=club, valid_to__isnull=False)
    assert sorted(ended.values_list("user_id", flat=True)) == [COORD, CO_COORD]
    # The former head is no longer a Club Head for this club.
    r = actors.student(COORD).post(f"{API}/clubs/{club.pk}/leadership",
                                   {"coordinator_user_id": COORD,
                                    "co_coordinator_user_id": CO_COORD}, format="json")
    assert r.status_code == 404


def test_uc_gym_008_swap_and_partial_change(actors, club):
    head = actors.student(COORD)
    r = head.post(f"{API}/clubs/{club.pk}/leadership",
                  {"coordinator_user_id": CO_COORD, "co_coordinator_user_id": COORD},
                  format="json")
    assert r.status_code == 200
    r = actors.student(COORD).post(f"{API}/clubs/{club.pk}/leadership",
                                   {"coordinator_user_id": CO_COORD,
                                    "co_coordinator_user_id": MEMBER}, format="json")
    assert r.status_code == 200
    assert LeadershipAssignment.objects.filter(club=club).count() == 5
    unchanged = actors.student(CO_COORD).post(
        f"{API}/clubs/{club.pk}/leadership",
        {"coordinator_user_id": CO_COORD, "co_coordinator_user_id": MEMBER}, format="json")
    assert unchanged.status_code == 200
    assert LeadershipAssignment.objects.filter(club=club).count() == 5


def test_uc_gym_008_exception_flow_invalid_leader_leaves_leadership_intact(actors, club):
    """BR-GYM-001."""
    head = actors.student(COORD)
    for coord, co in ((COUNCILLOR, PLAIN), (PLAIN, PLAIN), (424242, PLAIN)):
        r = head.post(f"{API}/clubs/{club.pk}/leadership",
                      {"coordinator_user_id": coord, "co_coordinator_user_id": co},
                      format="json")
        assert r.status_code == 422
    assert sorted(LeadershipAssignment.objects.filter(valid_to__isnull=True)
                  .values_list("user_id", flat=True)) == [COORD, CO_COORD]


# -- Budget --------------------------------------------------------------------
def test_uc_gym_009_club_head_submits_an_open_budget_request(actors, club):
    """CFR-GYM-006, AFR-GYM-029, AFR-GYM-031."""
    head = actors.student(COORD)
    r = head.post(f"{API}/budget-requests/create",
                  {"club_id": club.pk, "purpose": "Parts", "description": "Motors",
                   "amount": "0.00", "document_url": DRIVE}, format="json")
    assert r.status_code == 201, r.content
    assert r.json()["status"] == "open" and r.json()["document_link"] == DRIVE
    assert [b["id"] for b in head.get(f"{API}/budget-requests").json()["results"]] \
        == [r.json()["id"]]


def test_uc_gym_009_exception_flow_negative_amount_or_missing_file(actors, club):
    """BR-GYM-017, BR-GYM-018, AFR-GYM-030."""
    head = actors.student(COORD)
    base = {"club_id": club.pk, "purpose": "Parts", "description": "Motors",
            "amount": "10.00", "document_url": DRIVE}
    r = head.post(f"{API}/budget-requests/create", {**base, "amount": "-1.00"},
                  format="json")
    assert r.json()["error"]["code"] == "negative_amount"
    r = head.post(f"{API}/budget-requests/create", {**base, "document_url": ""},
                  format="json")
    assert r.json()["error"]["code"] == "supporting_file_required"
    r = head.post(f"{API}/budget-requests/create", {**base, "purpose": ""}, format="json")
    assert r.status_code == 422
    assert not BudgetRequest.objects.exists()


# -- Reports -------------------------------------------------------------------
def report_body(club_id, **kw):
    body = {"club_id": club_id, "student_incharge_user_id": MEMBER,
            "event_name": "RoboWars",
            "event_at": (timezone.now() - timedelta(days=1)).isoformat(),
            "description": "Went well", "report_url": DRIVE}
    body.update(kw)
    return body


def test_uc_gym_010_and_012_report_submitted_then_reviewed_by_the_councillor(actors, club):
    """CFR-GYM-007, AFR-GYM-032, AFR-GYM-034, BR-GYM-021."""
    r = actors.student(COORD).post(f"{API}/event-reports/create", report_body(club.pk),
                                   format="json")
    assert r.status_code == 201, r.content
    rid = r.json()["id"]
    councillor = actors.faculty(COUNCILLOR)
    assert [x["id"] for x in councillor.get(f"{API}/event-reports").json()["results"]] \
        == [rid]
    detail = councillor.get(f"{API}/event-reports/{rid}")
    assert detail.status_code == 200 and detail.json()["report_link"] == DRIVE
    assert detail.json()["student_incharge_name"] == f"Student {MEMBER} (stu{MEMBER})"
    listed = councillor.get(f"{API}/event-reports").json()["results"][0]
    assert listed["student_incharge_name"] == f"Student {MEMBER} (stu{MEMBER})"


def test_uc_gym_012_exception_flow_another_faculty_is_denied(actors, club):
    """BR-GYM-021: 404, not 403."""
    rid = actors.student(COORD).post(f"{API}/event-reports/create", report_body(club.pk),
                                     format="json").json()["id"]
    other = actors.faculty(OTHER_FACULTY)
    assert other.get(f"{API}/event-reports").json()["results"] == []
    assert other.get(f"{API}/event-reports/{rid}").status_code == 404


def test_uc_gym_010_exception_flows(actors, club):
    """BR-GYM-019, AFR-GYM-033: missing file, non-student in charge, future event."""
    head = actors.student(COORD)
    for body, err in ((report_body(club.pk, report_url=""), "report_file_required"),
                      (report_body(club.pk, student_incharge_user_id=COUNCILLOR),
                       "invalid_student"),
                      (report_body(club.pk, event_at=(timezone.now() + timedelta(days=1))
                                   .isoformat()), "event_not_yet_held"),
                      (report_body(club.pk, event_name=""), "missing_field")):
        r = head.post(f"{API}/event-reports/create", body, format="json")
        assert r.json()["error"]["code"] == err, body
    assert not EventReport.objects.exists()


# -- My clubs and the people picker -------------------------------------------
def test_my_clubs_lists_led_and_joined_clubs(actors, club, other_club):
    join(other_club, COORD)
    body = actors.student(COORD).get(f"{API}/me/clubs").json()
    assert [c["name"] for c in body["leading"]] == ["Robotics"]
    assert [c["name"] for c in body["member_of"]] == ["Dramatics"]
    assert actors.student(PLAIN).get(f"{API}/me/clubs").json() == {"leading": [],
                                                                   "member_of": []}


def test_people_picker_for_a_club_head(actors, club):
    from fusion_auth.client import UserRef
    head = actors.student(COORD)
    actors.fake.search_users = lambda q="", kind=None, limit=25: [
        UserRef(user_id=1, username="stu1", display_name="One", kind="student"),
        UserRef(user_id=2, username="fac2", display_name="Two", kind="faculty")]
    r = head.get(f"{API}/people?q=stu&kind=student")
    assert r.status_code == 200 and [p["user_id"] for p in r.json()] == [1]
    assert head.get(f"{API}/people?q=s&kind=student").json() == []
    assert head.get(f"{API}/people?q=stu&kind=staff").status_code == 400


def test_uc_gym_010_r3_04_a_report_dated_before_the_club_existed_is_refused(actors, club):
    Club.objects.filter(pk=club.pk).update(created_at=timezone.now() - timedelta(days=10))
    early = (timezone.now() - timedelta(days=30)).isoformat()
    r = actors.student(COORD).post(f"{API}/event-reports/create",
                                   report_body(club.pk, event_at=early), format="json")
    assert r.status_code == 422 and r.json()["error"]["code"] == "event_before_club"
    assert not EventReport.objects.exists()
