"""Every live use case, end to end through HTTP only."""
import datetime

import pytest

from modules.gymkhana.models import (
    Club,
    ClubBudgetRequest,
    ClubEventReport,
    ClubLeadershipHistory,
    ClubMembership,
    Poll,
    VenueBooking,
)
from modules.gymkhana.tests.support import (
    ADMIN,
    API,
    CO_HEAD,
    COUNCILLOR,
    HEAD,
    OTHER_HEAD,
    OTHER_STUDENT,
    STUDENT,
    make_club,
    make_poll,
    new_poll,
    now,
    people,
    sign_in,
    slot,
    upload,
)

pytestmark = pytest.mark.django_db

NEW_CLUB = {
    "name": "Chess Club", "category": "Sports", "description": "Plays chess",
    "coordinator_id": HEAD, "co_coordinator_id": CO_HEAD, "faculty_councillor_id": COUNCILLOR,
}


@pytest.fixture(autouse=True)
def _people(stub_iam):
    people()


def admin(stub_iam):
    return sign_in(stub_iam, ADMIN, "student", "student_admin")


# -- BW-GYM-03: UC-GYM-001 and UC-GYM-011 ---------------------------------------
def test_uc_gym_001_011_a_club_is_created_open_then_approved(stub_iam):
    """CFR-GYM-001, AFR-GYM-001, AFR-GYM-005, AFR-GYM-006."""
    created = admin(stub_iam).post(f"{API}/clubs/", NEW_CLUB, format="json")
    assert created.status_code == 201
    assert (created.json()["status"], created.json()["category"]) == ("open", "sports")
    assert created.json()["coordinator_name"] == f"User {HEAD}"
    pk = created.json()["id"]
    student = sign_in(stub_iam, STUDENT)
    assert student.get(f"{API}/clubs/{pk}/").status_code == 404
    assert admin(stub_iam).post(f"{API}/clubs/{pk}/confirm/").json()["status"] == "confirmed"
    assert sign_in(stub_iam, STUDENT).get(f"{API}/clubs/{pk}/").status_code == 200


@pytest.mark.parametrize(("field", "value"), [
    ("coordinator_id", COUNCILLOR), ("co_coordinator_id", 999999),
    ("faculty_councillor_id", STUDENT), ("category", "Business"),
])
def test_uc_gym_001_an_invalid_assignment_creates_nothing(stub_iam, field, value):
    """AFR-GYM-002, AFR-GYM-003, AFR-GYM-004."""
    response = admin(stub_iam).post(f"{API}/clubs/", {**NEW_CLUB, field: value}, format="json")
    assert response.status_code == 400
    assert not Club.objects.exists()


def test_uc_gym_011_a_confirmed_club_cannot_be_approved_again(stub_iam):
    club = make_club()
    assert admin(stub_iam).post(f"{API}/clubs/{club.pk}/confirm/").status_code == 409


# -- UC-GYM-002 and UC-GYM-003 ---------------------------------------------------
def test_uc_gym_002_a_head_books_a_session_everyone_can_see(stub_iam):
    """CFR-GYM-003, AFR-GYM-010."""
    club = make_club()
    booked = sign_in(stub_iam, CO_HEAD).post(f"{API}/bookings/session/", slot(club), format="json")
    assert booked.status_code == 201
    listed = sign_in(stub_iam, STUDENT).get(f"{API}/bookings/?venue=Hall 1&booking_date=2027-03-01")
    assert [b["id"] for b in listed.json()["results"]] == [booked.json()["id"]]


def test_uc_gym_003_a_head_books_an_event_with_a_poster(stub_iam):
    """AFR-GYM-014."""
    club = make_club()
    body = {**slot(club), "name": "Tech Talk", "faculty_councillor_id": COUNCILLOR,
            "poster_file": upload("poster.png", b"png")}
    booked = sign_in(stub_iam, HEAD).post(f"{API}/bookings/event/", body, format="multipart")
    assert booked.status_code == 201
    assert booked.json()["poster_file"]


@pytest.mark.parametrize("second", ["session", "event"])
@pytest.mark.parametrize("first", ["session", "event"])
def test_uc_gym_002_003_an_overlap_is_refused_across_types(stub_iam, first, second):
    """AFR-GYM-012."""
    club = make_club()
    client = sign_in(stub_iam, HEAD)
    body = {**slot(club), "name": "X", "faculty_councillor_id": COUNCILLOR}
    assert client.post(f"{API}/bookings/{first}/", body, format="json").status_code == 201
    overlap = {**body, "start_time": "10:30", "end_time": "11:30"}
    assert client.post(f"{API}/bookings/{second}/", overlap, format="json").status_code == 409
    assert VenueBooking.objects.count() == 1


@pytest.mark.parametrize("change", [
    {"venue": "The Moon"}, {"start_time": "11:00"}, {"start_time": "12:00"},
    {"faculty_councillor_id": STUDENT},
])
def test_uc_gym_003_an_invalid_event_is_not_recorded(stub_iam, change):
    """AFR-GYM-011."""
    body = {**slot(make_club()), "name": "X", "faculty_councillor_id": COUNCILLOR, **change}
    response = sign_in(stub_iam, HEAD).post(f"{API}/bookings/event/", body, format="json")
    assert response.status_code == 400
    assert not VenueBooking.objects.exists()


def test_uc_gym_002_only_the_clubs_own_heads_book_and_only_once_confirmed(stub_iam):
    club, waiting = make_club(), make_club("Drama", status="open")
    refused = sign_in(stub_iam, STUDENT).post(f"{API}/bookings/session/", slot(club))
    assert refused.status_code == 403
    early = sign_in(stub_iam, HEAD).post(f"{API}/bookings/session/", slot(waiting))
    assert early.status_code == 409


# -- BW-GYM-01: UC-GYM-004 and UC-GYM-005 ----------------------------------------
def test_uc_gym_004_005_an_application_becomes_a_membership(stub_iam):
    """CFR-GYM-004, AFR-GYM-016, AFR-GYM-019, AFR-GYM-020, AFR-GYM-021, AFR-GYM-022, BR-GYM-011."""
    club = make_club()
    body = {"club_id": club.pk, "description": "Won a contest"}
    applied = sign_in(stub_iam, STUDENT).post(f"{API}/memberships/apply/", body, format="json")
    assert (applied.status_code, applied.json()["status"]) == (201, "open")
    head = sign_in(stub_iam, HEAD)
    pending = head.get(f"{API}/memberships/?club_id={club.pk}").json()["results"]
    assert [m["student_name"] for m in pending] == [f"User {STUDENT}"]
    approved = head.post(
        f"{API}/memberships/{pending[0]['id']}/approve/", {"remarks": "Welcome"}, format="json")
    assert (approved.json()["status"], approved.json()["remarks"]) == ("confirmed", "Welcome")
    mine = sign_in(stub_iam, STUDENT).get(f"{API}/memberships/").json()["results"]
    assert mine[0]["status"] == "confirmed"


def test_uc_gym_004_a_second_club_is_allowed_and_a_duplicate_is_not(stub_iam):
    """AFR-GYM-017, AFR-GYM-018, BR-GYM-008."""
    one, two, waiting = make_club(), make_club("Music"), make_club("Drama", status="open")
    client = sign_in(stub_iam, STUDENT)

    def apply(club):
        return client.post(f"{API}/memberships/apply/", {"club_id": club.pk}).status_code

    assert [apply(one), apply(two), apply(one), apply(waiting)] == [201, 201, 409, 409]
    assert ClubMembership.objects.count() == 2


def test_uc_gym_005_an_approved_application_is_not_changed_again(stub_iam):
    row = ClubMembership.objects.create(club=make_club(), student_id=STUDENT)
    client = sign_in(stub_iam, HEAD)
    url = f"{API}/memberships/{row.pk}/approve/"
    assert client.post(url, {"remarks": "first"}).status_code == 200
    assert client.post(url, {"remarks": "second"}).status_code == 409
    row.refresh_from_db()
    assert row.remarks == "first"


# -- BW-GYM-02: UC-GYM-006 and UC-GYM-007 ----------------------------------------
def test_uc_gym_006_007_a_targeted_student_votes_once(stub_iam):
    """CFR-GYM-005, AFR-GYM-023, AFR-GYM-026, AFR-GYM-027, AFR-GYM-028."""
    club = make_club()
    created = sign_in(stub_iam, HEAD).post(f"{API}/polls/", new_poll(club), format="json")
    assert created.status_code == 201
    student = sign_in(stub_iam, STUDENT)
    poll = student.get(f"{API}/polls/").json()["results"][0]
    assert poll["has_voted"] is False
    url, body = f"{API}/polls/{poll['id']}/vote/", {"choice_id": poll["choices"][0]["id"]}
    voted = student.post(url, body, format="json")
    assert (voted.status_code, voted.json()["has_voted"]) == (200, True)
    assert sum(c["vote_count"] for c in voted.json()["choices"]) == 1
    assert student.post(url, body, format="json").status_code == 409
    outsider = sign_in(stub_iam, OTHER_STUDENT)
    assert outsider.post(url, body, format="json").status_code == 403


@pytest.mark.parametrize("change", [
    {"choices": ["Only one"]}, {"choices": ["Same", "Same"]}, {"target_groups": []},
    {"target_groups": [{"batch": "soon", "branch": "CSE"}]},
    {"target_groups": [{"batch": "2024"}]}, {"expires_at": "2020-01-01T00:00:00Z"},
])
def test_uc_gym_006_an_invalid_poll_is_not_created(stub_iam, change):
    """AFR-GYM-024, BR-GYM-012, BR-GYM-013."""
    body = new_poll(make_club(), **change)
    assert sign_in(stub_iam, HEAD).post(f"{API}/polls/", body, format="json").status_code == 400
    assert not Poll.objects.exists()


def test_uc_gym_006_a_repeated_target_group_counts_once(stub_iam):
    group = {"batch": "2024", "branch": "CSE"}
    body = new_poll(make_club(), target_groups=[group, group])
    created = sign_in(stub_iam, HEAD).post(f"{API}/polls/", body, format="json")
    assert created.json()["target_groups"] == [group]


def test_uc_gym_007_an_expired_poll_takes_no_vote(stub_iam):
    poll = make_poll(make_club(), expires_in=-datetime.timedelta(seconds=1))
    body = {"choice_id": poll.choices.first().pk}
    response = sign_in(stub_iam, STUDENT).post(f"{API}/polls/{poll.pk}/vote/", body)
    assert response.status_code == 400
    assert poll.choices.first().vote_count == 0


# -- UC-GYM-008 --------------------------------------------------------------------
def test_uc_gym_008_a_handover_moves_authority_at_once(stub_iam):
    """CFR-GYM-002, AFR-GYM-007, AFR-GYM-009, BR-GYM-016."""
    club = make_club()
    body = {"coordinator_id": STUDENT, "co_coordinator_id": OTHER_STUDENT}
    url = f"{API}/clubs/{club.pk}/leadership/"
    assert sign_in(stub_iam, HEAD).post(url, body, format="json").status_code == 200
    assert ClubLeadershipHistory.objects.get().changed_by_id == HEAD
    assert sign_in(stub_iam, HEAD).post(url, body, format="json").status_code == 403
    booked = sign_in(stub_iam, STUDENT).post(f"{API}/bookings/session/", slot(club), format="json")
    assert booked.status_code == 201


def test_uc_gym_008_an_invalid_or_unauthorised_change_leaves_leaders_alone(stub_iam):
    """AFR-GYM-008."""
    club = make_club()
    url = f"{API}/clubs/{club.pk}/leadership/"
    invalid = {"coordinator_id": COUNCILLOR, "co_coordinator_id": STUDENT}
    valid = {"coordinator_id": STUDENT, "co_coordinator_id": OTHER_STUDENT}
    assert sign_in(stub_iam, HEAD).post(url, invalid, format="json").status_code == 400
    assert sign_in(stub_iam, OTHER_HEAD).post(url, valid, format="json").status_code == 403
    club.refresh_from_db()
    assert (club.coordinator_id, club.co_coordinator_id) == (HEAD, CO_HEAD)


# -- UC-GYM-009 --------------------------------------------------------------------
def test_uc_gym_009_a_budget_request_is_stored_open(stub_iam):
    """CFR-GYM-006, AFR-GYM-029, AFR-GYM-031."""
    club = make_club()
    client = sign_in(stub_iam, HEAD)
    body = {"club_id": club.pk, "amount": "0", "purpose": "Kit", "supporting_file": upload()}
    sent = client.post(f"{API}/budgets/", body, format="multipart")
    assert (sent.status_code, sent.json()["status"]) == (201, "open")
    listed = client.get(f"{API}/budgets/?club_id={club.pk}").json()["results"]
    assert [b["id"] for b in listed] == [sent.json()["id"]]


@pytest.mark.parametrize("change", [{"amount": "-1"}, {"supporting_file": None}])
def test_uc_gym_009_an_invalid_request_is_not_stored(stub_iam, change):
    """AFR-GYM-030, BR-GYM-017, BR-GYM-018."""
    body = {"club_id": make_club().pk, "amount": "5", "purpose": "Kit",
            "supporting_file": upload(), **change}
    body = {k: v for k, v in body.items() if v is not None}
    response = sign_in(stub_iam, HEAD).post(f"{API}/budgets/", body, format="multipart")
    assert response.status_code == 400
    assert not ClubBudgetRequest.objects.exists()


# -- UC-GYM-010 and UC-GYM-012 -----------------------------------------------------
def report_body(club, **changes):
    return {"club_id": club.pk, "student_incharge_id": STUDENT, "event_name": "Expo",
            "event_date": "2026-11-01T10:00:00Z", "description": "Went well",
            "report_file": upload(content=b"%PDF report"), **changes}


def test_uc_gym_010_012_a_report_reaches_its_councillor(stub_iam):
    """CFR-GYM-007, AFR-GYM-032, AFR-GYM-034."""
    club = make_club()
    sent = sign_in(stub_iam, HEAD).post(f"{API}/reports/", report_body(club), format="multipart")
    assert sent.status_code == 201
    councillor = sign_in(stub_iam, COUNCILLOR, "faculty")
    row = councillor.get(f"{API}/reports/").json()["results"][0]
    assert (row["event_name"], row["student_incharge_name"]) == ("Expo", f"User {STUDENT}")
    file = councillor.get(f"/api/v1{row['report_file']}")
    assert b"".join(file.streaming_content) == b"%PDF report"


@pytest.mark.parametrize("change", [
    {"report_file": None}, {"student_incharge_id": COUNCILLOR}, {"event_date": "future"},
])
def test_uc_gym_010_an_incomplete_report_is_not_accepted(stub_iam, change):
    """AFR-GYM-033, BR-GYM-019."""
    if change.get("event_date"):
        change = {"event_date": (now() + datetime.timedelta(days=1)).isoformat()}
    body = {k: v for k, v in report_body(make_club(), **change).items() if v is not None}
    response = sign_in(stub_iam, HEAD).post(f"{API}/reports/", body, format="multipart")
    assert response.status_code == 400
    assert not ClubEventReport.objects.exists()
