from datetime import date, timedelta

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
from modules.gymkhana.models.poll import PollChoice, PollVote, VotingPoll
from modules.gymkhana.models.report import ClubEventReport

pytestmark = pytest.mark.django_db


@pytest.fixture
def spec_club():
    UserRef.objects.bulk_create(
        [
            UserRef(
                user_id=101,
                username="br101",
                display_name="Coordinator",
                kind="student",
                batch_year=2020,
                discipline="MATH",
            ),
            UserRef(
                user_id=102,
                username="br102",
                display_name="Co-coordinator",
                kind="student",
                batch_year=2020,
                discipline="MATH",
            ),
            UserRef(
                user_id=103,
                username="br103",
                display_name="Target student",
                kind="student",
                batch_year=2023,
                discipline="CSE",
            ),
            UserRef(
                user_id=104,
                username="br104",
                display_name="Other student",
                kind="student",
                batch_year=2024,
                discipline="ECE",
            ),
            UserRef(
                user_id=201,
                username="br201",
                display_name="Assigned faculty",
                kind="faculty",
            ),
            UserRef(
                user_id=202,
                username="br202",
                display_name="Other faculty",
                kind="faculty",
            ),
        ]
    )
    club = Club.objects.create(
        name="BR specification club",
        category="Cultural",
        description="",
        faculty_councillor_id=201,
        status="confirmed",
    )
    ClubLeadership.objects.create(
        club=club, student_id=101, role="coordinator", is_current=True
    )
    ClubLeadership.objects.create(
        club=club, student_id=102, role="co_coordinator", is_current=True
    )
    return club


def _client(stub_iam, user_id, *permissions, kind="student", role="student"):
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


def _admin_client(stub_iam):
    return _client(
        stub_iam,
        201,
        "gymkhana.club.create",
        "gymkhana.club.approve",
        kind="faculty",
        role="student_admin",
    )


def _club_payload(name="BR-created club", **overrides):
    payload = {
        "name": name,
        "category": "Technical",
        "description": "Specification test",
        "coordinator_id": 101,
        "co_coordinator_id": 102,
        "faculty_councillor_id": 201,
    }
    payload.update(overrides)
    return payload


def _create_poll(client, club_id, *, batches=None, branches=None, expires_at=None, choices=None):
    return client.post(
        f"/api/v1/gymkhana/clubs/{club_id}/polls/",
        {
            "title": "BR specification poll",
            "target_batches": batches if batches is not None else ["2023"],
            "target_branches": branches if branches is not None else ["CSE"],
            "expires_at": (
                expires_at or (timezone.now() + timedelta(days=2))
            ).isoformat(),
            "choices": choices if choices is not None else ["Yes", "No"],
        },
        format="json",
    )


def _booking_payload(**overrides):
    payload = {
        "title": "Specification booking",
        "venue": "L-101",
        "date": (date.today() + timedelta(days=30)).isoformat(),
        "start_time": "10:00:00",
        "end_time": "11:00:00",
        "description": "Specification test booking",
    }
    payload.update(overrides)
    return payload


def _book(client, club_id, booking_type="sessions", **overrides):
    return client.post(
        f"/api/v1/gymkhana/clubs/{club_id}/{booking_type}/",
        _booking_payload(**overrides),
        format="json",
    )


def _upload(name):
    return SimpleUploadedFile(name, b"specification test content", content_type="application/pdf")


def _submit_budget(client, club_id, **overrides):
    payload = {
        "amount": "100.00",
        "purpose": "Specification test",
        "description": "Budget request test",
        "supporting_file": _upload("support.pdf"),
    }
    payload.update(overrides)
    return client.post(
        f"/api/v1/gymkhana/clubs/{club_id}/budgets/",
        payload,
        format="multipart",
    )


def _submit_report(client, club_id, **overrides):
    payload = {
        "title": "Specification report",
        "description": "Report test",
        "student_incharge_id": 103,
        "event_name": "Specification event",
        "event_datetime": (timezone.now() + timedelta(days=1)).isoformat(),
        "report_file": _upload("report.pdf"),
    }
    payload.update(overrides)
    return client.post(
        f"/api/v1/gymkhana/clubs/{club_id}/reports/submit/",
        payload,
        format="multipart",
    )


def test_br_gym_001_positive_valid_student_assignments(stub_iam, spec_club):
    """test_id=BR-GYM-001-POSITIVE; source_id=BR-GYM-001 — valid student assignment."""
    response = _admin_client(stub_iam).post(
        "/api/v1/gymkhana/clubs/",
        _club_payload(),
        format="json",
    )

    assert response.status_code == 201
    current = {
        leader["role"]: leader["student_id"]
        for leader in response.json()["leaderships"]
        if leader["is_current"]
    }
    assert current == {"coordinator": 101, "co_coordinator": 102}
    assert ClubLeadership.objects.filter(club_id=response.json()["id"], is_current=True).count() == 2


@pytest.mark.parametrize(
    ("assignment", "expected_club_count"),
    [
        ("coordinator", 1),
        ("co_coordinator", 1),
        ("replacement", 1),
    ],
)
def test_br_gym_001_negative_invalid_student_assignment(
    stub_iam, spec_club, assignment, expected_club_count
):
    """test_id=BR-GYM-001-NEGATIVE; source_id=BR-GYM-001 — invalid student assignment."""
    before_clubs = Club.objects.count()
    before_leadership = list(
        ClubLeadership.objects.filter(club=spec_club, is_current=True).values_list(
            "student_id", "role"
        )
    )
    if assignment == "replacement":
        client = _client(stub_iam, 101, "gymkhana.leadership.update")
        response = client.post(
            f"/api/v1/gymkhana/clubs/{spec_club.id}/leadership/",
            {"new_coordinator_id": 103, "new_co_coordinator_id": 999},
            format="json",
        )
    else:
        client = _admin_client(stub_iam)
        field = "coordinator_id" if assignment == "coordinator" else "co_coordinator_id"
        response = client.post(
            "/api/v1/gymkhana/clubs/",
            _club_payload(name=f"Invalid {assignment}", **{field: 999}),
            format="json",
        )

    assert response.status_code == 422
    assert Club.objects.count() == before_clubs == expected_club_count
    assert list(
        ClubLeadership.objects.filter(club=spec_club, is_current=True).values_list(
            "student_id", "role"
        )
    ) == before_leadership


def test_br_gym_002_positive_valid_faculty_assignment(stub_iam, spec_club):
    """test_id=BR-GYM-002-POSITIVE; source_id=BR-GYM-002 — valid faculty councillor."""
    response = _admin_client(stub_iam).post(
        "/api/v1/gymkhana/clubs/",
        _club_payload(name="Valid faculty club"),
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["faculty_councillor_id"] == 201


def test_br_gym_002_negative_invalid_faculty_assignment(stub_iam, spec_club):
    """test_id=BR-GYM-002-NEGATIVE; source_id=BR-GYM-002 — invalid faculty councillor."""
    before = Club.objects.count()
    response = _admin_client(stub_iam).post(
        "/api/v1/gymkhana/clubs/",
        _club_payload(name="Invalid faculty club", faculty_councillor_id=999),
        format="json",
    )

    assert response.status_code == 422
    assert Club.objects.count() == before


@pytest.mark.parametrize("category", ["Technical", "Sports", "Cultural"])
def test_br_gym_003_allowed_categories(stub_iam, spec_club, category):
    """test_id=BR-GYM-003-ALLOWED; source_id=BR-GYM-003 — allowed category values."""
    response = _admin_client(stub_iam).post(
        "/api/v1/gymkhana/clubs/",
        _club_payload(name=f"Allowed {category} club", category=category),
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["category"] == category


def test_br_gym_003_negative_disallowed_category(stub_iam, spec_club):
    """test_id=BR-GYM-003-NEGATIVE; source_id=BR-GYM-003 — disallowed category."""
    before = Club.objects.count()
    response = _admin_client(stub_iam).post(
        "/api/v1/gymkhana/clubs/",
        _club_payload(name="Disallowed category club", category="Academic"),
        format="json",
    )

    assert response.status_code == 422
    assert Club.objects.count() == before


def test_br_gym_004_creation_starts_open(stub_iam, spec_club):
    """test_id=BR-GYM-004-CREATION; source_id=BR-GYM-004 — club creation lifecycle."""
    response = _admin_client(stub_iam).post(
        "/api/v1/gymkhana/clubs/",
        _club_payload(name="Open lifecycle club"),
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["status"] == "open"


def test_br_gym_004_student_admin_approval_confirms_club(stub_iam, spec_club):
    """test_id=BR-GYM-004-APPROVAL; source_id=BR-GYM-004 — Student Admin approval."""
    club = Club.objects.create(
        name="Open approval club",
        category="Sports",
        faculty_councillor_id=201,
        status="open",
    )
    response = _admin_client(stub_iam).post(f"/api/v1/gymkhana/clubs/{club.id}/confirm/")

    assert response.status_code == 200
    club.refresh_from_db()
    assert response.json()["status"] == "confirmed"
    assert club.status == "confirmed"


@pytest.mark.parametrize("booking_type", ["sessions", "events"])
def test_br_gym_005_valid_booking_time_range(stub_iam, spec_club, booking_type):
    """test_id=BR-GYM-005-VALID; source_id=BR-GYM-005 — valid time range."""
    client = _client(
        stub_iam,
        101,
        "gymkhana.session.book",
        "gymkhana.event.book",
    )
    response = _book(client, spec_club.id, booking_type, start_time="10:00:00", end_time="11:00:00")

    assert response.status_code == 201
    assert ClubBooking.objects.filter(pk=response.json()["id"]).exists()


@pytest.mark.parametrize(
    ("start_time", "end_time"),
    [("10:00:00", "10:00:00"), ("11:00:00", "10:00:00")],
)
@pytest.mark.parametrize("booking_type", ["sessions", "events"])
def test_br_gym_005_invalid_booking_time_range(
    stub_iam, spec_club, start_time, end_time, booking_type
):
    """test_id=BR-GYM-005-INVALID; source_id=BR-GYM-005 — invalid time range."""
    client = _client(
        stub_iam,
        101,
        "gymkhana.session.book",
        "gymkhana.event.book",
    )
    before = ClubBooking.objects.count()
    response = _book(
        client,
        spec_club.id,
        booking_type,
        start_time=start_time,
        end_time=end_time,
    )

    assert response.status_code == 422
    assert ClubBooking.objects.count() == before


def test_br_gym_006_session_session_overlap_rejected(stub_iam, spec_club):
    """test_id=BR-GYM-006-SESSION-SESSION; source_id=BR-GYM-006 — session-session overlap."""
    client = _client(stub_iam, 101, "gymkhana.session.book")
    assert _book(client, spec_club.id, "sessions").status_code == 201
    before = ClubBooking.objects.count()
    response = _book(
        client,
        spec_club.id,
        "sessions",
        start_time="10:30:00",
        end_time="11:30:00",
    )

    assert response.status_code == 409
    assert ClubBooking.objects.count() == before


def test_br_gym_006_event_event_overlap_rejected(stub_iam, spec_club):
    """test_id=BR-GYM-006-EVENT-EVENT; source_id=BR-GYM-006 — event-event overlap."""
    client = _client(stub_iam, 101, "gymkhana.event.book")
    assert _book(client, spec_club.id, "events").status_code == 201
    before = ClubBooking.objects.count()
    response = _book(
        client,
        spec_club.id,
        "events",
        start_time="10:30:00",
        end_time="11:30:00",
    )

    assert response.status_code == 409
    assert ClubBooking.objects.count() == before


@pytest.mark.parametrize(
    ("existing_type", "new_type"),
    [("sessions", "events"), ("events", "sessions")],
)
def test_br_gym_006_session_event_overlap_rejected(stub_iam, spec_club, existing_type, new_type):
    """test_id=BR-GYM-006-SESSION-EVENT; source_id=BR-GYM-006 — session-event overlap."""
    client = _client(
        stub_iam,
        101,
        "gymkhana.session.book",
        "gymkhana.event.book",
    )
    assert _book(client, spec_club.id, existing_type).status_code == 201
    before = ClubBooking.objects.count()
    response = _book(
        client,
        spec_club.id,
        new_type,
        start_time="10:30:00",
        end_time="11:30:00",
    )

    assert response.status_code == 409
    assert ClubBooking.objects.count() == before


def test_br_gym_006_non_overlapping_booking_is_allowed(stub_iam, spec_club):
    """test_id=BR-GYM-006-NO-OVERLAP; source_id=BR-GYM-006 — permitted non-overlapping booking."""
    client = _client(
        stub_iam,
        101,
        "gymkhana.session.book",
        "gymkhana.event.book",
    )
    assert _book(client, spec_club.id, "sessions").status_code == 201
    response = _book(
        client,
        spec_club.id,
        "events",
        start_time="11:00:00",
        end_time="12:00:00",
    )

    assert response.status_code == 201
    assert ClubBooking.objects.filter(pk=response.json()["id"]).exists()


def test_br_gym_007_confirmed_club_allows_membership_application(stub_iam, spec_club):
    """test_id=BR-GYM-007-CONFIRMED; source_id=BR-GYM-007 — confirmed club application."""
    client = _client(stub_iam, 103, "gymkhana.membership.apply")
    response = client.post(
        f"/api/v1/gymkhana/clubs/{spec_club.id}/memberships/apply/",
        {"remarks": "Interested"},
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["status"] == "open"
    assert ClubMembership.objects.filter(
        pk=response.json()["id"], club=spec_club, student_id=103, status="open"
    ).exists()


def test_br_gym_007_open_club_rejects_membership_application(stub_iam, spec_club):
    """test_id=BR-GYM-007-OPEN; source_id=BR-GYM-007 — open club application."""
    spec_club.status = "open"
    spec_club.save(update_fields=["status"])
    before = ClubMembership.objects.count()
    response = _client(stub_iam, 103, "gymkhana.membership.apply").post(
        f"/api/v1/gymkhana/clubs/{spec_club.id}/memberships/apply/",
        {},
        format="json",
    )

    assert response.status_code == 409
    assert ClubMembership.objects.count() == before


def test_br_gym_008_different_club_applications_are_allowed(stub_iam, spec_club):
    """test_id=BR-GYM-008-DIFFERENT-CLUBS; source_id=BR-GYM-008 — multiple different-club applications."""
    other_club = Club.objects.create(
        name="Second confirmed club",
        category="Sports",
        faculty_councillor_id=201,
        status="confirmed",
    )
    client = _client(stub_iam, 103, "gymkhana.membership.apply")
    first = client.post(
        f"/api/v1/gymkhana/clubs/{spec_club.id}/memberships/apply/", {}, format="json"
    )
    second = client.post(
        f"/api/v1/gymkhana/clubs/{other_club.id}/memberships/apply/", {}, format="json"
    )

    assert first.status_code == second.status_code == 201
    assert ClubMembership.objects.filter(student_id=103, club__in=[spec_club, other_club]).count() == 2


def test_br_gym_009_duplicate_same_club_application_is_rejected(stub_iam, spec_club):
    """test_id=BR-GYM-009-DUPLICATE; source_id=BR-GYM-009 — duplicate same-club application."""
    client = _client(stub_iam, 103, "gymkhana.membership.apply")
    first = client.post(
        f"/api/v1/gymkhana/clubs/{spec_club.id}/memberships/apply/",
        {"remarks": "Original"},
        format="json",
    )
    assert first.status_code == 201
    before = list(
        ClubMembership.objects.filter(club=spec_club, student_id=103).values_list(
            "id", "status", "remarks"
        )
    )
    duplicate = client.post(
        f"/api/v1/gymkhana/clubs/{spec_club.id}/memberships/apply/",
        {"remarks": "Duplicate"},
        format="json",
    )

    assert duplicate.status_code == 409
    assert list(
        ClubMembership.objects.filter(club=spec_club, student_id=103).values_list(
            "id", "status", "remarks"
        )
    ) == before


@pytest.mark.parametrize("head_id", [101, 102])
def test_br_gym_010_applicable_club_head_is_authorized(stub_iam, spec_club, head_id):
    """test_id=BR-GYM-010-AUTHORIZED; source_id=BR-GYM-010 — applicable Club Head authorization."""
    client = _client(stub_iam, head_id, "gymkhana.session.book")
    response = _book(client, spec_club.id, "sessions")

    assert response.status_code == 201
    assert ClubBooking.objects.filter(pk=response.json()["id"]).exists()


def test_br_gym_010_non_head_is_not_authorized(stub_iam, spec_club):
    """test_id=BR-GYM-010-UNAUTHORIZED; source_id=BR-GYM-010 — unauthorized Club Head."""
    before = ClubBooking.objects.count()
    response = _book(
        _client(stub_iam, 103, "gymkhana.session.book"),
        spec_club.id,
        "sessions",
    )

    assert response.status_code == 403
    assert ClubBooking.objects.count() == before


def test_br_gym_011_membership_approval_confirms_and_retains_remarks(stub_iam, spec_club):
    """test_id=BR-GYM-011-APPROVAL; source_id=BR-GYM-011 — membership approval transition."""
    application = ClubMembership.objects.create(
        club=spec_club,
        student_id=103,
        status="open",
        remarks="Application remarks",
    )
    response = _client(stub_iam, 102, "gymkhana.membership.approve").post(
        f"/api/v1/gymkhana/memberships/{application.id}/approve/",
        {"remarks": "Welcome"},
        format="json",
    )

    assert response.status_code == 200
    application.refresh_from_db()
    assert application.status == response.json()["status"] == "confirmed"
    assert application.remarks == response.json()["remarks"] == "Welcome"


def test_br_gym_012_poll_requires_minimum_choices(stub_iam, spec_club):
    """test_id=BR-GYM-012-MINIMUM; source_id=BR-GYM-012 — minimum poll choices."""
    client = _client(stub_iam, 101, "gymkhana.poll.create")
    before = VotingPoll.objects.count()
    rejected = _create_poll(client, spec_club.id, choices=["Only choice"])

    assert rejected.status_code == 422
    assert VotingPoll.objects.count() == before

    accepted = _create_poll(client, spec_club.id, choices=["First", "Second"])
    assert accepted.status_code == 201
    assert PollChoice.objects.filter(poll_id=accepted.json()["id"]).count() == 2


def test_br_gym_013_poll_notifications_use_selected_audience(stub_iam, spec_club):
    """test_id=BR-GYM-013-TARGET-AUDIENCE; source_id=BR-GYM-013 — poll target audience."""
    client = _client(stub_iam, 101, "gymkhana.poll.create")
    response = _create_poll(client, spec_club.id, batches=["2023"], branches=["CSE"])

    assert response.status_code == 201
    recipients = set(
        GymkhanaNotificationOutbox.objects.filter(topic="gymkhana.poll.created").values_list(
            "recipient_user_id", flat=True
        )
    )
    assert recipients == {103}
    assert response.json()["target_batches"] == ["2023"]
    assert response.json()["target_branches"] == ["CSE"]


def test_br_gym_014_active_unexpired_poll_allows_eligible_student(stub_iam, spec_club):
    """test_id=BR-GYM-014-ACTIVE-ELIGIBLE; source_id=BR-GYM-014 — active eligible participation."""
    creation = _create_poll(
        _client(stub_iam, 101, "gymkhana.poll.create"),
        spec_club.id,
    )
    assert creation.status_code == 201
    poll_id = creation.json()["id"]
    choice_id = creation.json()["choices"][0]["id"]

    student = _client(stub_iam, 103, "gymkhana.poll.vote")
    available = student.get("/api/v1/gymkhana/polls/")
    vote = student.post(
        f"/api/v1/gymkhana/polls/{poll_id}/vote/",
        {"choice_id": choice_id},
        format="json",
    )

    assert available.status_code == 200
    assert poll_id in {poll["id"] for poll in available.json()}
    assert vote.status_code == 200
    assert PollVote.objects.filter(poll_id=poll_id, student_id=103).count() == 1


@pytest.mark.skip(
    reason="NOT_AUTOMATED: The poll model and API expose expiry but no separate active/inactive state."
)
def test_br_gym_014_inactive_poll_denies_participation(stub_iam, spec_club):
    """test_id=BR-GYM-014-INACTIVE; source_id=BR-GYM-014 — inactive poll."""
    pytest.fail("A poll cannot be prepared in an inactive-but-unexpired state through available interfaces.")


def test_br_gym_014_expired_poll_denies_participation(stub_iam, spec_club):
    """test_id=BR-GYM-014-EXPIRED; source_id=BR-GYM-014 — expired poll."""
    expired = _create_poll(
        _client(stub_iam, 101, "gymkhana.poll.create"),
        spec_club.id,
        expires_at=timezone.now() - timedelta(days=1),
    )
    assert expired.status_code == 201
    poll_id = expired.json()["id"]
    choice_id = expired.json()["choices"][0]["id"]
    before = PollVote.objects.filter(poll_id=poll_id).count()
    response = _client(stub_iam, 103, "gymkhana.poll.vote").post(
        f"/api/v1/gymkhana/polls/{poll_id}/vote/",
        {"choice_id": choice_id},
        format="json",
    )

    assert response.status_code == 409
    assert PollVote.objects.filter(poll_id=poll_id).count() == before


def test_br_gym_014_non_target_student_cannot_vote(stub_iam, spec_club):
    """test_id=BR-GYM-014-NON-TARGET; source_id=BR-GYM-014 — student outside target audience."""
    poll = _create_poll(
        _client(stub_iam, 101, "gymkhana.poll.create"),
        spec_club.id,
        batches=["2023"],
        branches=["CSE"],
    )
    assert poll.status_code == 201
    poll_id = poll.json()["id"]
    before = PollVote.objects.filter(poll_id=poll_id).count()
    response = _client(stub_iam, 104, "gymkhana.poll.vote").post(
        f"/api/v1/gymkhana/polls/{poll_id}/vote/",
        {"choice_id": poll.json()["choices"][0]["id"]},
        format="json",
    )

    assert response.status_code == 403
    assert PollVote.objects.filter(poll_id=poll_id).count() == before


def test_br_gym_015_first_vote_is_accepted(stub_iam, spec_club):
    """test_id=BR-GYM-015-FIRST-VOTE; source_id=BR-GYM-015 — first vote."""
    poll = _create_poll(
        _client(stub_iam, 101, "gymkhana.poll.create"),
        spec_club.id,
    )
    assert poll.status_code == 201
    poll_id = poll.json()["id"]
    response = _client(stub_iam, 103, "gymkhana.poll.vote").post(
        f"/api/v1/gymkhana/polls/{poll_id}/vote/",
        {"choice_id": poll.json()["choices"][0]["id"]},
        format="json",
    )

    assert response.status_code == 200
    assert PollVote.objects.filter(poll_id=poll_id, student_id=103).count() == 1


def test_br_gym_015_second_vote_is_rejected_without_change(stub_iam, spec_club):
    """test_id=BR-GYM-015-SECOND-VOTE; source_id=BR-GYM-015 — duplicate vote."""
    poll = _create_poll(
        _client(stub_iam, 101, "gymkhana.poll.create"),
        spec_club.id,
    )
    assert poll.status_code == 201
    poll_id = poll.json()["id"]
    choice_id = poll.json()["choices"][0]["id"]
    student = _client(stub_iam, 103, "gymkhana.poll.vote")
    first = student.post(
        f"/api/v1/gymkhana/polls/{poll_id}/vote/",
        {"choice_id": choice_id},
        format="json",
    )
    assert first.status_code == 200
    before_votes = PollVote.objects.filter(poll_id=poll_id, student_id=103).count()
    before_choice_count = PollChoice.objects.get(pk=choice_id).votes_count

    second = student.post(
        f"/api/v1/gymkhana/polls/{poll_id}/vote/",
        {"choice_id": choice_id},
        format="json",
    )

    assert second.status_code == 409
    assert PollVote.objects.filter(poll_id=poll_id, student_id=103).count() == before_votes
    assert PollChoice.objects.get(pk=choice_id).votes_count == before_choice_count


def test_br_gym_016_leadership_succession_replaces_current_leaders(stub_iam, spec_club):
    """test_id=BR-GYM-016-SUCCESSION; source_id=BR-GYM-016 — leadership succession."""
    response = _client(stub_iam, 101, "gymkhana.leadership.update").post(
        f"/api/v1/gymkhana/clubs/{spec_club.id}/leadership/",
        {"new_coordinator_id": 103, "new_co_coordinator_id": 104},
        format="json",
    )

    assert response.status_code == 200
    current = {
        leader["role"]: leader["student_id"]
        for leader in response.json()["leaderships"]
        if leader["is_current"]
    }
    assert current == {"coordinator": 103, "co_coordinator": 104}
    assert not ClubLeadership.objects.filter(
        club=spec_club, student_id__in=[101, 102], is_current=True
    ).exists()


def test_br_gym_017_zero_budget_amount_is_allowed(stub_iam, spec_club):
    """test_id=BR-GYM-017-ZERO; source_id=BR-GYM-017 — zero budget amount."""
    response = _submit_budget(
        _client(stub_iam, 101, "gymkhana.budget.request"),
        spec_club.id,
        amount="0.00",
    )

    assert response.status_code == 201
    assert ClubBudgetRequest.objects.get(pk=response.json()["id"]).amount == 0


def test_br_gym_017_negative_budget_amount_is_rejected(stub_iam, spec_club):
    """test_id=BR-GYM-017-NEGATIVE; source_id=BR-GYM-017 — negative budget amount."""
    before = ClubBudgetRequest.objects.count()
    response = _submit_budget(
        _client(stub_iam, 101, "gymkhana.budget.request"),
        spec_club.id,
        amount="-1.00",
    )

    assert response.status_code == 422
    assert ClubBudgetRequest.objects.count() == before


def test_br_gym_018_budget_request_with_supporting_file_is_stored(stub_iam, spec_club):
    """test_id=BR-GYM-018-PRESENT; source_id=BR-GYM-018 — budget supporting file present."""
    response = _submit_budget(
        _client(stub_iam, 101, "gymkhana.budget.request"),
        spec_club.id,
    )

    assert response.status_code == 201
    request = ClubBudgetRequest.objects.get(pk=response.json()["id"])
    assert request.supporting_file
    assert request.amount >= 0


def test_br_gym_018_budget_request_without_supporting_file_is_rejected(stub_iam, spec_club):
    """test_id=BR-GYM-018-MISSING; source_id=BR-GYM-018 — budget supporting file missing."""
    before = ClubBudgetRequest.objects.count()
    response = _submit_budget(
        _client(stub_iam, 101, "gymkhana.budget.request"),
        spec_club.id,
        supporting_file="",
    )

    assert response.status_code == 422
    assert ClubBudgetRequest.objects.count() == before


def test_br_gym_019_report_with_required_file_is_stored(stub_iam, spec_club):
    """test_id=BR-GYM-019-PRESENT; source_id=BR-GYM-019 — event report file present."""
    response = _submit_report(
        _client(stub_iam, 101, "gymkhana.report.submit"),
        spec_club.id,
    )

    assert response.status_code == 201
    report = ClubEventReport.objects.get(pk=response.json()["id"])
    assert report.report_file
    assert report.club == spec_club


def test_br_gym_019_report_without_required_file_is_rejected(stub_iam, spec_club):
    """test_id=BR-GYM-019-MISSING; source_id=BR-GYM-019 — event report file missing."""
    before = ClubEventReport.objects.count()
    response = _submit_report(
        _client(stub_iam, 101, "gymkhana.report.submit"),
        spec_club.id,
        report_file="",
    )

    assert response.status_code == 422
    assert ClubEventReport.objects.count() == before


def test_br_gym_020_configured_venue_is_accepted(stub_iam, spec_club):
    """test_id=BR-GYM-020-CONFIGURED; source_id=BR-GYM-020 — configured venue."""
    response = _book(
        _client(stub_iam, 101, "gymkhana.session.book"),
        spec_club.id,
        "sessions",
        venue="L-101",
    )

    assert response.status_code == 201
    assert ClubBooking.objects.get(pk=response.json()["id"]).venue == "L-101"


def test_br_gym_020_unconfigured_venue_is_rejected(stub_iam, spec_club):
    """test_id=BR-GYM-020-UNCONFIGURED; source_id=BR-GYM-020 — unconfigured venue."""
    before = ClubBooking.objects.count()
    response = _book(
        _client(stub_iam, 101, "gymkhana.session.book"),
        spec_club.id,
        "sessions",
        venue="Unconfigured venue",
    )

    assert response.status_code == 422
    assert ClubBooking.objects.count() == before


def test_br_gym_021_assigned_faculty_can_access_report(stub_iam, spec_club):
    """test_id=BR-GYM-021-ASSIGNED-FACULTY; source_id=BR-GYM-021 — assigned faculty report access."""
    submitted = _submit_report(
        _client(stub_iam, 101, "gymkhana.report.submit"),
        spec_club.id,
    )
    assert submitted.status_code == 201
    report_id = submitted.json()["id"]

    response = _client(
        stub_iam,
        201,
        "gymkhana.report.review",
        kind="faculty",
        role="faculty",
    ).get(f"/api/v1/gymkhana/reports/{report_id}/file/")

    assert response.status_code == 200
    assert ClubEventReport.objects.filter(pk=report_id, club=spec_club).exists()


def test_br_gym_021_nonassigned_faculty_cannot_access_report(stub_iam, spec_club):
    """test_id=BR-GYM-021-NONASSIGNED-FACULTY; source_id=BR-GYM-021 — nonassigned faculty report access."""
    submitted = _submit_report(
        _client(stub_iam, 101, "gymkhana.report.submit"),
        spec_club.id,
    )
    assert submitted.status_code == 201
    report_id = submitted.json()["id"]
    before = ClubEventReport.objects.count()

    response = _client(
        stub_iam,
        202,
        "gymkhana.report.review",
        kind="faculty",
        role="faculty",
    ).get(f"/api/v1/gymkhana/reports/{report_id}/file/")

    assert response.status_code == 404
    assert ClubEventReport.objects.count() == before
