from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.gymkhana.models.booking import ClubBooking
from modules.gymkhana.models.budget import ClubBudgetRequest
from modules.gymkhana.models.club import Club, ClubLeadership
from modules.gymkhana.models.membership import ClubMembership
from modules.gymkhana.models.notification import GymkhanaNotificationOutbox
from modules.gymkhana.models.poll import PollVote, VotingPoll
from modules.gymkhana.models.report import ClubEventReport
from modules.gymkhana.storage import gymkhana_upload_storage

pytestmark = pytest.mark.django_db


@pytest.fixture
def gymkhana_setup():
    UserRef.objects.create(
        user_id=101,
        username="s101",
        display_name="Coordinator",
        kind="student",
        batch_year=2023,
        discipline="CSE",
    )
    UserRef.objects.create(
        user_id=102,
        username="s102",
        display_name="Co-coordinator",
        kind="student",
        batch_year=2023,
        discipline="CSE",
    )
    UserRef.objects.create(
        user_id=103,
        username="s103",
        display_name="Target student",
        kind="student",
        batch_year=2023,
        discipline="CSE",
    )
    UserRef.objects.create(
        user_id=104,
        username="s104",
        display_name="Other student",
        kind="student",
        batch_year=2022,
        discipline="EE",
    )
    UserRef.objects.create(
        user_id=201,
        username="f201",
        display_name="Faculty Councillor",
        kind="faculty",
    )
    UserRef.objects.create(
        user_id=202,
        username="f202",
        display_name="Student Admin",
        kind="faculty",
    )

    club = Club.objects.create(
        name="Specification Club",
        category="Cultural",
        description="A club for specification tests.",
        faculty_councillor_id=201,
        status="confirmed",
    )
    ClubLeadership.objects.create(
        club=club,
        student_id=101,
        role="coordinator",
        is_current=True,
    )
    ClubLeadership.objects.create(
        club=club,
        student_id=102,
        role="co_coordinator",
        is_current=True,
    )
    return club


@pytest.fixture(autouse=True)
def isolated_upload_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(gymkhana_upload_storage, "_location", str(tmp_path))
    gymkhana_upload_storage.__dict__.pop("location", None)
    yield
    gymkhana_upload_storage.__dict__.pop("location", None)


def _client(stub_iam, *, user_id, permissions, kind="student"):
    role = "student_admin" if "gymkhana.club.create" in permissions else kind
    stub_iam(
        make_session(
            user_id=user_id,
            permissions=permissions,
            modules=("gymkhana",),
            kind=kind,
            roles=(role,),
            active_role=role,
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock_token")
    return client


def _club_payload(**overrides):
    payload = {
        "name": "New Specification Club",
        "category": "Technical",
        "description": "A valid club.",
        "coordinator_id": 101,
        "co_coordinator_id": 102,
        "faculty_councillor_id": 201,
    }
    payload.update(overrides)
    return payload


def _booking_payload(*, title, start_time="10:00:00", end_time="12:00:00"):
    return {
        "title": title,
        "venue": "L-101",
        "date": str(date.today() + timedelta(days=10)),
        "start_time": start_time,
        "end_time": end_time,
        "description": "Specification booking.",
    }


def _booking_request(client, club_id, booking_type, payload):
    path = "sessions" if booking_type == "session" else "events"
    return client.post(
        f"/api/v1/gymkhana/clubs/{club_id}/{path}/",
        payload,
        format="json",
    )


def _poll_payload(**overrides):
    payload = {
        "title": "Specification poll",
        "description": "Choose an option.",
        "target_batches": ["2023"],
        "target_branches": ["CSE"],
        "expires_at": (timezone.now() + timedelta(days=2)).isoformat(),
        "choices": ["Option A", "Option B"],
    }
    payload.update(overrides)
    return payload


def _upload(name):
    return SimpleUploadedFile(name, b"specification test file", content_type="application/pdf")


def _assert_refused(response, expected_status):
    assert response.status_code == expected_status, response.content
    assert "error" in response.json()


def test_gym_bw03_001(stub_iam, gymkhana_setup):
    """GYM-BW03-001; source_id: BW-GYM-03 transition 1/UC-GYM-001 and transition 2/UC-GYM-011."""
    admin = _client(
        stub_iam,
        user_id=202,
        kind="faculty",
        permissions=("gymkhana.club.create", "gymkhana.club.approve"),
    )
    created = admin.post("/api/v1/gymkhana/clubs/", _club_payload(), format="json")
    assert created.status_code == 201
    assert created.json()["status"] == "open"

    confirmed = admin.post(f"/api/v1/gymkhana/clubs/{created.json()['id']}/confirm/")
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"


def test_gym_br_gym_001_001_invalid_coordinator_refused(stub_iam, gymkhana_setup):
    """GYM-BR-GYM-001-001; source_id: BR-GYM-001 false outcome."""
    admin = _client(
        stub_iam,
        user_id=202,
        kind="faculty",
        permissions=("gymkhana.club.create",),
    )
    before = Club.objects.count()

    response = admin.post(
        "/api/v1/gymkhana/clubs/",
        _club_payload(coordinator_id=999),
        format="json",
    )

    _assert_refused(response, 422)
    assert Club.objects.count() == before


def test_gym_br_gym_002_001_invalid_co_coordinator_refused(stub_iam, gymkhana_setup):
    """GYM-BR-GYM-002-001; source_id: BR-GYM-002 false outcome."""
    admin = _client(
        stub_iam,
        user_id=202,
        kind="faculty",
        permissions=("gymkhana.club.create",),
    )
    before = Club.objects.count()

    response = admin.post(
        "/api/v1/gymkhana/clubs/",
        _club_payload(co_coordinator_id=999),
        format="json",
    )

    _assert_refused(response, 422)
    assert Club.objects.count() == before


def test_gym_br_gym_003_001_invalid_faculty_councillor_refused(stub_iam, gymkhana_setup):
    """GYM-BR-GYM-003-001; source_id: BR-GYM-003 false outcome."""
    admin = _client(
        stub_iam,
        user_id=202,
        kind="faculty",
        permissions=("gymkhana.club.create",),
    )
    before = Club.objects.count()

    response = admin.post(
        "/api/v1/gymkhana/clubs/",
        _club_payload(faculty_councillor_id=999),
        format="json",
    )

    _assert_refused(response, 422)
    assert Club.objects.count() == before


def test_gym_br_gym_004_001_invalid_category_refused(stub_iam, gymkhana_setup):
    """GYM-BR-GYM-004-001; source_id: BR-GYM-004 category false outcome."""
    admin = _client(
        stub_iam,
        user_id=202,
        kind="faculty",
        permissions=("gymkhana.club.create",),
    )
    before = Club.objects.count()

    response = admin.post(
        "/api/v1/gymkhana/clubs/",
        _club_payload(category="Arts"),
        format="json",
    )

    _assert_refused(response, 422)
    assert Club.objects.count() == before


def test_gym_br_gym_004_002_missing_required_data_refused(stub_iam, gymkhana_setup):
    """GYM-BR-GYM-004-002; source_id: BR-GYM-004 required data false outcome."""
    admin = _client(
        stub_iam,
        user_id=202,
        kind="faculty",
        permissions=("gymkhana.club.create",),
    )
    payload = _club_payload()
    payload.pop("name")
    before = Club.objects.count()

    response = admin.post("/api/v1/gymkhana/clubs/", payload, format="json")

    _assert_refused(response, 422)
    assert Club.objects.count() == before


def test_gym_bw01_001(stub_iam, gymkhana_setup):
    """GYM-BW01-001; source_id: BW-GYM-01 transition 1/UC-GYM-004 and transition 2/UC-GYM-005."""
    student = _client(stub_iam, user_id=103, permissions=("gymkhana.membership.apply",))
    applied = student.post(
        f"/api/v1/gymkhana/clubs/{gymkhana_setup.id}/memberships/apply/",
        {"remarks": "Please consider my application."},
        format="json",
    )
    assert applied.status_code == 201
    assert applied.json()["status"] == "open"

    head = _client(stub_iam, user_id=101, permissions=("gymkhana.membership.approve",))
    approved = head.post(
        f"/api/v1/gymkhana/memberships/{applied.json()['id']}/approve/",
        {"remarks": "Approved."},
        format="json",
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "confirmed"


def test_gym_br_gym_007_001_open_club_application_refused(stub_iam, gymkhana_setup):
    """GYM-BR-GYM-007-001; source_id: BR-GYM-007 application guard false outcome."""
    gymkhana_setup.status = "open"
    gymkhana_setup.save(update_fields=["status"])
    student = _client(stub_iam, user_id=103, permissions=("gymkhana.membership.apply",))
    before = ClubMembership.objects.count()

    response = student.post(
        f"/api/v1/gymkhana/clubs/{gymkhana_setup.id}/memberships/apply/",
        {},
        format="json",
    )

    _assert_refused(response, 409)
    assert ClubMembership.objects.count() == before


def test_gym_br_gym_008_001_duplicate_club_application_refused(stub_iam, gymkhana_setup):
    """GYM-BR-GYM-008-001; source_id: BR-GYM-008 duplicate guard false outcome."""
    ClubMembership.objects.create(club=gymkhana_setup, student_id=103, status="open")
    student = _client(stub_iam, user_id=103, permissions=("gymkhana.membership.apply",))
    before = ClubMembership.objects.count()

    response = student.post(
        f"/api/v1/gymkhana/clubs/{gymkhana_setup.id}/memberships/apply/",
        {},
        format="json",
    )

    _assert_refused(response, 409)
    assert ClubMembership.objects.count() == before


def test_gym_br_gym_009_001_multiple_club_applications_allowed(stub_iam, gymkhana_setup):
    """GYM-BR-GYM-009-001; source_id: BR-GYM-009 multiple-club guard true outcome."""
    second_club = Club.objects.create(
        name="Second Specification Club",
        category="Sports",
        faculty_councillor_id=201,
        status="confirmed",
    )
    student = _client(stub_iam, user_id=103, permissions=("gymkhana.membership.apply",))

    first = student.post(
        f"/api/v1/gymkhana/clubs/{gymkhana_setup.id}/memberships/apply/",
        {},
        format="json",
    )
    second = student.post(
        f"/api/v1/gymkhana/clubs/{second_club.id}/memberships/apply/",
        {},
        format="json",
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert set(
        ClubMembership.objects.filter(student_id=103).values_list("club_id", flat=True)
    ) == {gymkhana_setup.id, second_club.id}


def test_gym_br_gym_010_001_non_head_cannot_approve(stub_iam, gymkhana_setup):
    """GYM-BR-GYM-010-001; source_id: BR-GYM-010 approval authorization false outcome."""
    membership = ClubMembership.objects.create(
        club=gymkhana_setup,
        student_id=104,
        status="open",
    )
    other_student = _client(stub_iam, user_id=103, permissions=("gymkhana.membership.approve",))

    response = other_student.post(
        f"/api/v1/gymkhana/memberships/{membership.id}/approve/",
        {},
        format="json",
    )

    _assert_refused(response, 403)
    membership.refresh_from_db()
    assert membership.status == "open"
    assert membership.confirmed_at is None


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: The available Gymkhana API persists notification outbox entries, "
        "but no notification delivery interface or worker is available to verify delivery."
    )
)
def test_gym_bw02_001(stub_iam, gymkhana_setup):
    """GYM-BW02-001; source_id: BW-GYM-02 transition 1/UC-GYM-006 and transition 2/UC-GYM-007."""
    leader = _client(stub_iam, user_id=101, permissions=("gymkhana.poll.create",))
    created = leader.post(
        f"/api/v1/gymkhana/clubs/{gymkhana_setup.id}/polls/",
        _poll_payload(),
        format="json",
    )
    assert created.status_code == 201

    student = _client(stub_iam, user_id=103, permissions=("gymkhana.poll.vote",))
    vote = student.post(
        f"/api/v1/gymkhana/polls/{created.json()['id']}/vote/",
        {"choice_id": created.json()["choices"][0]["id"]},
        format="json",
    )
    assert vote.status_code == 200


def test_gym_br_gym_012_001_poll_requires_two_choices(stub_iam, gymkhana_setup):
    """GYM-BR-GYM-012-001; source_id: BR-GYM-012 choice-count false outcome."""
    leader = _client(stub_iam, user_id=101, permissions=("gymkhana.poll.create",))
    before = VotingPoll.objects.count()

    response = leader.post(
        f"/api/v1/gymkhana/clubs/{gymkhana_setup.id}/polls/",
        _poll_payload(choices=["Only choice"]),
        format="json",
    )

    _assert_refused(response, 422)
    assert VotingPoll.objects.count() == before


def test_gym_br_gym_012_002_poll_requires_target_groups(stub_iam, gymkhana_setup):
    """GYM-BR-GYM-012-002; source_id: BR-GYM-012 target-group false outcome."""
    leader = _client(stub_iam, user_id=101, permissions=("gymkhana.poll.create",))
    before = VotingPoll.objects.count()

    response = leader.post(
        f"/api/v1/gymkhana/clubs/{gymkhana_setup.id}/polls/",
        _poll_payload(target_batches=[]),
        format="json",
    )

    _assert_refused(response, 422)
    assert VotingPoll.objects.count() == before


def test_gym_br_gym_013_001_non_target_student_cannot_vote(stub_iam, gymkhana_setup):
    """GYM-BR-GYM-013-001; source_id: BR-GYM-013 target-audience false outcome."""
    leader = _client(stub_iam, user_id=101, permissions=("gymkhana.poll.create",))
    created = leader.post(
        f"/api/v1/gymkhana/clubs/{gymkhana_setup.id}/polls/",
        _poll_payload(),
        format="json",
    )
    assert created.status_code == 201
    outsider = _client(stub_iam, user_id=104, permissions=("gymkhana.poll.vote",))
    before = PollVote.objects.count()

    response = outsider.post(
        f"/api/v1/gymkhana/polls/{created.json()['id']}/vote/",
        {"choice_id": created.json()["choices"][0]["id"]},
        format="json",
    )

    _assert_refused(response, 403)
    assert PollVote.objects.count() == before


def test_gym_br_gym_014_001_expired_poll_vote_refused(stub_iam, gymkhana_setup):
    """GYM-BR-GYM-014-001; source_id: BR-GYM-014 active-poll false outcome."""
    leader = _client(stub_iam, user_id=101, permissions=("gymkhana.poll.create",))
    created = leader.post(
        f"/api/v1/gymkhana/clubs/{gymkhana_setup.id}/polls/",
        _poll_payload(expires_at=(timezone.now() - timedelta(days=1)).isoformat()),
        format="json",
    )
    assert created.status_code == 201
    student = _client(stub_iam, user_id=103, permissions=("gymkhana.poll.vote",))
    before = PollVote.objects.count()

    response = student.post(
        f"/api/v1/gymkhana/polls/{created.json()['id']}/vote/",
        {"choice_id": created.json()["choices"][0]["id"]},
        format="json",
    )

    _assert_refused(response, 409)
    assert PollVote.objects.count() == before


def test_gym_br_gym_015_001_student_can_vote_only_once(stub_iam, gymkhana_setup):
    """GYM-BR-GYM-015-001; source_id: BR-GYM-015 one-vote-per-student false outcome."""
    leader = _client(stub_iam, user_id=101, permissions=("gymkhana.poll.create",))
    created = leader.post(
        f"/api/v1/gymkhana/clubs/{gymkhana_setup.id}/polls/",
        _poll_payload(),
        format="json",
    )
    assert created.status_code == 201
    student = _client(stub_iam, user_id=103, permissions=("gymkhana.poll.vote",))
    vote_url = f"/api/v1/gymkhana/polls/{created.json()['id']}/vote/"
    choice_id = created.json()["choices"][0]["id"]
    first = student.post(vote_url, {"choice_id": choice_id}, format="json")
    assert first.status_code == 200
    before_votes = PollVote.objects.filter(poll_id=created.json()["id"]).count()

    second = student.post(
        vote_url,
        {"choice_id": created.json()["choices"][1]["id"]},
        format="json",
    )

    _assert_refused(second, 409)
    assert PollVote.objects.filter(poll_id=created.json()["id"]).count() == before_votes == 1
    assert PollVote.objects.get(poll_id=created.json()["id"]).choice_id == choice_id


@pytest.mark.parametrize(
    ("booking_type", "start_time", "end_time"),
    [
        ("session", "10:00:00", "10:00:00"),
        ("session", "11:00:00", "10:00:00"),
        ("event", "10:00:00", "10:00:00"),
        ("event", "11:00:00", "10:00:00"),
    ],
)
def test_gym_section62_001_booking_requires_increasing_time(
    stub_iam, gymkhana_setup, booking_type, start_time, end_time
):
    """GYM-SECTION62-001; source_id: Section 6.2 Venue Scheduling - invalid time range."""
    leader = _client(
        stub_iam,
        user_id=101,
        permissions=("gymkhana.session.book", "gymkhana.event.book"),
    )
    before = ClubBooking.objects.count()

    response = _booking_request(
        leader,
        gymkhana_setup.id,
        booking_type,
        _booking_payload(
            title="Invalid time booking",
            start_time=start_time,
            end_time=end_time,
        ),
    )

    _assert_refused(response, 422)
    assert ClubBooking.objects.count() == before


def test_gym_section62_002_session_session_overlap_refused(stub_iam, gymkhana_setup):
    """GYM-SECTION62-002; source_id: Section 6.2 Venue Scheduling - session-session overlap."""
    leader = _client(stub_iam, user_id=101, permissions=("gymkhana.session.book",))
    first = _booking_request(
        leader,
        gymkhana_setup.id,
        "session",
        _booking_payload(title="First session"),
    )
    assert first.status_code == 201
    before = ClubBooking.objects.count()

    response = _booking_request(
        leader,
        gymkhana_setup.id,
        "session",
        _booking_payload(title="Overlapping session", start_time="11:00:00"),
    )

    _assert_refused(response, 409)
    assert ClubBooking.objects.count() == before


def test_gym_section62_003_event_event_overlap_refused(stub_iam, gymkhana_setup):
    """GYM-SECTION62-003; source_id: Section 6.2 Venue Scheduling - event-event overlap."""
    leader = _client(stub_iam, user_id=101, permissions=("gymkhana.event.book",))
    first = _booking_request(
        leader,
        gymkhana_setup.id,
        "event",
        _booking_payload(title="First event"),
    )
    assert first.status_code == 201
    before = ClubBooking.objects.count()

    response = _booking_request(
        leader,
        gymkhana_setup.id,
        "event",
        _booking_payload(title="Overlapping event", start_time="11:00:00"),
    )

    _assert_refused(response, 409)
    assert ClubBooking.objects.count() == before


def test_gym_section62_004_session_event_overlap_refused(stub_iam, gymkhana_setup):
    """GYM-SECTION62-004; source_id: Section 6.2 Venue Scheduling - session-event overlap."""
    leader = _client(
        stub_iam,
        user_id=101,
        permissions=("gymkhana.session.book", "gymkhana.event.book"),
    )
    first = _booking_request(
        leader,
        gymkhana_setup.id,
        "session",
        _booking_payload(title="First session"),
    )
    assert first.status_code == 201
    before = ClubBooking.objects.count()

    response = _booking_request(
        leader,
        gymkhana_setup.id,
        "event",
        _booking_payload(title="Overlapping event", start_time="11:00:00"),
    )

    _assert_refused(response, 409)
    assert ClubBooking.objects.count() == before


def test_gym_section62_005_adjacent_booking_is_allowed(stub_iam, gymkhana_setup):
    """GYM-SECTION62-005; source_id: Section 6.2 Venue Scheduling - non-overlap true outcome."""
    leader = _client(
        stub_iam,
        user_id=101,
        permissions=("gymkhana.session.book", "gymkhana.event.book"),
    )
    first = _booking_request(
        leader,
        gymkhana_setup.id,
        "event",
        _booking_payload(title="First activity"),
    )
    assert first.status_code == 201

    second = _booking_request(
        leader,
        gymkhana_setup.id,
        "session",
        _booking_payload(
            title="Adjacent activity",
            start_time="12:00:00",
            end_time="13:00:00",
        ),
    )

    assert second.status_code == 201
    assert ClubBooking.objects.filter(venue="L-101").count() == 2


def test_gym_section61_001_valid_leadership_change(stub_iam, gymkhana_setup):
    """GYM-SECTION61-001; source_id: Section 6.1 Club Governance - leadership maintenance."""
    leader = _client(stub_iam, user_id=101, permissions=("gymkhana.leadership.update",))

    response = leader.post(
        f"/api/v1/gymkhana/clubs/{gymkhana_setup.id}/leadership/",
        {"new_coordinator_id": 103, "new_co_coordinator_id": 102},
        format="json",
    )

    assert response.status_code == 200
    assert dict(
        ClubLeadership.objects.filter(club=gymkhana_setup, is_current=True).values_list(
            "role", "student_id"
        )
    ) == {"coordinator": 103, "co_coordinator": 102}


def test_gym_section61_002_invalid_leadership_change_refused(stub_iam, gymkhana_setup):
    """GYM-SECTION61-002; source_id: Section 6.1 Club Governance - invalid leadership false outcome."""
    leader = _client(stub_iam, user_id=101, permissions=("gymkhana.leadership.update",))
    before = set(
        ClubLeadership.objects.filter(club=gymkhana_setup, is_current=True).values_list(
            "role", "student_id"
        )
    )

    response = leader.post(
        f"/api/v1/gymkhana/clubs/{gymkhana_setup.id}/leadership/",
        {"new_coordinator_id": 999, "new_co_coordinator_id": 102},
        format="json",
    )

    _assert_refused(response, 422)
    assert set(
        ClubLeadership.objects.filter(club=gymkhana_setup, is_current=True).values_list(
            "role", "student_id"
        )
    ) == before


def test_gym_section63_001_confirmed_club_application_allowed(stub_iam, gymkhana_setup):
    """GYM-SECTION63-001; source_id: Section 6.3 Membership Management - confirmed-club application."""
    student = _client(stub_iam, user_id=103, permissions=("gymkhana.membership.apply",))

    response = student.post(
        f"/api/v1/gymkhana/clubs/{gymkhana_setup.id}/memberships/apply/",
        {},
        format="json",
    )

    assert response.status_code == 201
    membership = ClubMembership.objects.get(pk=response.json()["id"])
    assert membership.status == "open"
    assert membership.club_id == gymkhana_setup.id
    assert membership.student_id == 103


@pytest.mark.parametrize(
    ("amount", "expected_status", "expected_count"),
    [("-1.00", 422, 0), ("0.00", 201, 1)],
)
def test_gym_section66_001_budget_amount_is_non_negative(
    stub_iam, gymkhana_setup, amount, expected_status, expected_count
):
    """GYM-SECTION66-001; source_id: Section 6.6 Club Budget Requests - non-negative amount."""
    leader = _client(stub_iam, user_id=101, permissions=("gymkhana.budget.request",))
    before = ClubBudgetRequest.objects.count()

    response = leader.post(
        f"/api/v1/gymkhana/clubs/{gymkhana_setup.id}/budgets/",
        {
            "amount": amount,
            "purpose": "Equipment",
            "description": "Test budget request.",
            "supporting_file": _upload("budget.pdf"),
        },
        format="multipart",
    )

    if expected_status == 422:
        _assert_refused(response, expected_status)
        assert ClubBudgetRequest.objects.count() == before
    else:
        assert response.status_code == expected_status
        assert ClubBudgetRequest.objects.count() == before + expected_count
        assert ClubBudgetRequest.objects.get(pk=response.json()["id"]).amount == Decimal("0.00")


@pytest.mark.parametrize("include_file", [False, True], ids=["missing-file", "with-file"])
def test_gym_section66_002_budget_requires_file_and_stores_complete_request(
    stub_iam, gymkhana_setup, include_file
):
    """GYM-SECTION66-002; source_id: Section 6.6 Club Budget Requests - required supporting file."""
    leader = _client(stub_iam, user_id=101, permissions=("gymkhana.budget.request",))
    payload = {
        "amount": "125.00",
        "purpose": "Equipment",
        "description": "Test budget request.",
    }
    if include_file:
        payload["supporting_file"] = _upload("budget.pdf")
    before = ClubBudgetRequest.objects.count()

    response = leader.post(
        f"/api/v1/gymkhana/clubs/{gymkhana_setup.id}/budgets/",
        payload,
        format="multipart",
    )

    if not include_file:
        _assert_refused(response, 422)
        assert ClubBudgetRequest.objects.count() == before
    else:
        assert response.status_code == 201
        request = ClubBudgetRequest.objects.get(pk=response.json()["id"])
        assert request.club_id == gymkhana_setup.id
        assert request.supporting_file
        assert request.supporting_file.storage.exists(request.supporting_file.name)


@pytest.mark.parametrize("include_file", [False, True], ids=["missing-file", "with-file"])
def test_gym_section67_001_report_requires_file_and_stores_complete_report(
    stub_iam, gymkhana_setup, include_file
):
    """GYM-SECTION67-001; source_id: Section 6.7 Club Event Reports - required report file."""
    leader = _client(stub_iam, user_id=101, permissions=("gymkhana.report.submit",))
    payload = {
        "title": "Event report",
        "description": "Details of the event.",
        "student_incharge_id": 103,
        "event_name": "Club event",
        "event_datetime": datetime.now().astimezone().isoformat(),
    }
    if include_file:
        payload["report_file"] = _upload("report.pdf")
    before = ClubEventReport.objects.count()

    response = leader.post(
        f"/api/v1/gymkhana/clubs/{gymkhana_setup.id}/reports/submit/",
        payload,
        format="multipart",
    )

    if not include_file:
        _assert_refused(response, 422)
        assert ClubEventReport.objects.count() == before
    else:
        assert response.status_code == 201
        report = ClubEventReport.objects.get(pk=response.json()["id"])
        assert report.club_id == gymkhana_setup.id
        assert report.report_file
        assert report.report_file.storage.exists(report.report_file.name)


def test_gym_section67_002_assigned_councillor_can_access_report(stub_iam, gymkhana_setup):
    """GYM-SECTION67-002; source_id: Section 6.7 Club Event Reports - faculty councillor access."""
    head = _client(stub_iam, user_id=101, permissions=("gymkhana.report.submit",))
    submitted = head.post(
        f"/api/v1/gymkhana/clubs/{gymkhana_setup.id}/reports/submit/",
        {
            "title": "Event report",
            "description": "Details of the event.",
            "student_incharge_id": 103,
            "event_name": "Club event",
            "event_datetime": datetime.now().astimezone().isoformat(),
            "report_file": _upload("report.pdf"),
        },
        format="multipart",
    )
    assert submitted.status_code == 201

    councillor = _client(stub_iam, user_id=201, permissions=("gymkhana.report.review",))
    response = councillor.get(f"/api/v1/gymkhana/clubs/{gymkhana_setup.id}/reports/")

    assert response.status_code == 200
    assert [report["id"] for report in response.json()] == [submitted.json()["id"]]


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: The available Gymkhana API persists notification outbox entries, "
        "but no notification delivery interface or worker is available to verify delivery."
    )
)
def test_gym_section41_001_session_notification_delivered(stub_iam, gymkhana_setup):
    """GYM-SECTION41-001; source_id: Section 4.1 In Scope - session notification."""
    leader = _client(stub_iam, user_id=101, permissions=("gymkhana.session.book",))
    response = _booking_request(
        leader,
        gymkhana_setup.id,
        "session",
        _booking_payload(title="Notified session"),
    )
    assert response.status_code == 201
    assert GymkhanaNotificationOutbox.objects.filter(
        recipient_user_id=103,
        topic="gymkhana.session",
    ).exists()


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: The available Gymkhana API persists notification outbox entries, "
        "but no notification delivery interface or worker is available to verify delivery."
    )
)
def test_gym_section41_002_event_notification_delivered(stub_iam, gymkhana_setup):
    """GYM-SECTION41-002; source_id: Section 4.1 In Scope - event notification."""
    leader = _client(stub_iam, user_id=101, permissions=("gymkhana.event.book",))
    response = _booking_request(
        leader,
        gymkhana_setup.id,
        "event",
        _booking_payload(title="Notified event"),
    )
    assert response.status_code == 201
    assert GymkhanaNotificationOutbox.objects.filter(
        recipient_user_id=103,
        topic="gymkhana.event",
    ).exists()
