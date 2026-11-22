from datetime import timedelta

import pytest
from django.apps import apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.gymkhana import registry
from modules.gymkhana.models import (
    BudgetRequest,
    Club,
    ClubEvent,
    ClubEventReport,
    ClubSession,
    MembershipApplication,
    NotificationOutbox,
    PollChoice,
    PollTargetGroup,
    PollVote,
    VotingPoll,
)

pytestmark = pytest.mark.django_db

ROOT = "/api/v1/gymkhana"
ADMIN = tuple(registry.ROLE_GRANTS["Student Admin"])
FACULTY = tuple(registry.ROLE_GRANTS["faculty"])


def _client(stub_iam, *, user_id=2001, kind="student", role=None, permissions=None):
    role = role or kind
    grants = permissions if permissions is not None else registry.ROLE_GRANTS[role]
    stub_iam(make_session(
        user_id=user_id,
        kind=kind,
        roles=(role,),
        active_role=role,
        modules=("gymkhana",),
        permissions=grants,
    ))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token br-test")
    return client


def _person(user_id, kind="student", *, batch_year=2024, discipline="CSE"):
    user_ref = apps.get_model("directory", "UserRef")
    return user_ref.objects.create(
        user_id=user_id,
        username=f"u{user_id}",
        display_name=f"Person {user_id}",
        kind=kind,
        batch_year=batch_year if kind == "student" else None,
        discipline=discipline if kind == "student" else "",
    )


def _club(*, name="Robotics", status=Club.Status.CONFIRMED):
    return Club.objects.create(
        name=name,
        category=Club.Category.TECHNICAL,
        coordinator_user_id=2001,
        co_coordinator_user_id=2002,
        faculty_councillor_user_id=3001,
        description="Build things",
        status=status,
    )


def _create_poll(club, *, target_batch=2024, target_branch="CSE", active=True,
                 expires_at=None, choices=("Rover", "Drone")):
    poll = VotingPoll.objects.create(
        club=club,
        title="Choose a project",
        description="Select a project",
        expires_at=expires_at or timezone.now() + timedelta(days=2),
        created_by_user_id=club.coordinator_user_id,
        is_active=active,
    )
    PollChoice.objects.bulk_create([PollChoice(poll=poll, text=text) for text in choices])
    PollTargetGroup.objects.create(
        poll=poll,
        batch_year=target_batch,
        discipline=target_branch,
    )
    return poll


def _report_payload(*, student_id=4101, include_file=True):
    payload = {
        "student_incharge_user_id": student_id,
        "event_name": "Robot showcase",
        "event_at": "2026-11-01T12:00:00+05:30",
        "description": "Event summary",
    }
    if include_file:
        payload["report_file"] = SimpleUploadedFile("report.txt", b"event report")
    return payload


def test_gym_001_valid_club_creation_starts_open(stub_iam):
    """test_id=GYM-001; source_id=BR-GYM-001; BR-GYM-002; BR-GYM-003; BR-GYM-004"""
    _person(2001)
    _person(2002)
    _person(3001, "faculty")
    admin = _client(stub_iam, user_id=9001, role="Student Admin", permissions=ADMIN)

    for category in ("Technical", "Sports", "Cultural"):
        response = admin.post(
            f"{ROOT}/clubs",
            {
                "name": f"{category} Club",
                "description": "Valid club",
                "category": category,
                "coordinator_user_id": 2001,
                "co_coordinator_user_id": 2002,
                "faculty_councillor_user_id": 3001,
            },
            format="json",
        )

        assert response.status_code == 201, response.content
        assert response.json()["category"] == category
        assert response.json()["status"] == Club.Status.OPEN
        assert Club.objects.get(name=f"{category} Club").status == Club.Status.OPEN


def test_gym_002_invalid_leaders_faculty_and_category_are_rejected(stub_iam):
    """test_id=GYM-002; source_id=BR-GYM-001; BR-GYM-002; BR-GYM-003"""
    _person(2001)
    _person(2002)
    _person(3001, "faculty")
    admin = _client(stub_iam, user_id=9001, role="Student Admin", permissions=ADMIN)
    valid_data = {
        "description": "Candidate club",
        "category": "Technical",
        "coordinator_user_id": 2001,
        "co_coordinator_user_id": 2002,
        "faculty_councillor_user_id": 3001,
    }

    invalid_cases = (
        ("invalid coordinator", {"coordinator_user_id": 2991}),
        ("invalid co-coordinator", {"co_coordinator_user_id": 2992}),
        ("invalid faculty", {"faculty_councillor_user_id": 3991}),
        ("unsupported category", {"category": "Academic"}),
    )
    for index, (case_name, changes) in enumerate(invalid_cases):
        response = admin.post(
            f"{ROOT}/clubs",
            {**valid_data, **changes, "name": f"Invalid Club {index}"},
            format="json",
        )
        assert response.status_code in (400, 409), (case_name, response.content)
        assert not Club.objects.filter(name=f"Invalid Club {index}").exists()


def test_gym_003_only_student_admin_confirms_open_club(stub_iam):
    """test_id=GYM-003; source_id=BR-GYM-004; Problem Statement §4.1 In Scope"""
    club = _club(status=Club.Status.OPEN)
    non_admin = _client(stub_iam, user_id=2001)

    denied = non_admin.post(f"{ROOT}/clubs/{club.pk}/approve")

    assert denied.status_code == 403
    club.refresh_from_db()
    assert club.status == Club.Status.OPEN

    admin = _client(stub_iam, user_id=9001, role="Student Admin", permissions=ADMIN)
    approved = admin.post(f"{ROOT}/clubs/{club.pk}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == Club.Status.CONFIRMED
    club.refresh_from_db()
    assert club.status == Club.Status.CONFIRMED


def test_gym_004_leadership_change_replaces_current_leaders(stub_iam):
    """test_id=GYM-004; source_id=BR-GYM-001; BR-GYM-016"""
    club = _club()
    _person(2101)
    _person(2102)
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/leadership",
        {"coordinator_user_id": 2101, "co_coordinator_user_id": 2102},
        format="json",
    )

    assert response.status_code == 200, response.content
    club.refresh_from_db()
    assert (club.coordinator_user_id, club.co_coordinator_user_id) == (2101, 2102)
    assert club.coordinator_user_id not in (2001, 2002)
    assert club.co_coordinator_user_id not in (2001, 2002)


def test_gym_005_invalid_replacement_leader_is_rejected(stub_iam):
    """test_id=GYM-005; source_id=BR-GYM-001"""
    club = _club()
    _person(2102)
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/leadership",
        {"coordinator_user_id": 2999, "co_coordinator_user_id": 2102},
        format="json",
    )

    assert response.status_code == 409
    club.refresh_from_db()
    assert (club.coordinator_user_id, club.co_coordinator_user_id) == (2001, 2002)


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_gym_006_booking_start_time_must_precede_end_time(stub_iam):
    """test_id=GYM-006; source_id=BR-GYM-005"""
    club = _club()
    _person(3002, "faculty")
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    for index, (start, end, accepted) in enumerate((
        ("09:00", "10:00", True),
        ("10:00", "10:00", False),
        ("11:00", "10:00", False),
    )):
        session_response = head.post(
            f"{ROOT}/clubs/{club.pk}/sessions",
            {
                "venue": "Auditorium",
                "date": f"2026-12-0{index + 1}",
                "start_time": start,
                "end_time": end,
                "description": "Session",
            },
            format="json",
        )
        assert (session_response.status_code == 201) is accepted
        event_response = head.post(
            f"{ROOT}/clubs/{club.pk}/events",
            {
                "name": "Event",
                "faculty_user_id": 3002,
                "venue": "Auditorium",
                "date": f"2026-12-1{index + 1}",
                "start_time": start,
                "end_time": end,
                "description": "Event",
            },
            format="json",
        )
        assert (event_response.status_code == 201) is accepted


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_gym_007_overlaps_rejected_for_all_booking_type_pairs(stub_iam):
    """test_id=GYM-007; source_id=BR-GYM-006"""
    club = _club()
    _person(3002, "faculty")
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    ClubSession.objects.create(
        club=club, venue="Auditorium", date="2026-12-01",
        start_time="10:00", end_time="11:00", description="Existing session",
        created_by_user_id=club.coordinator_user_id,
    )
    ClubEvent.objects.create(
        club=club, name="Existing event", venue="Auditorium", date="2026-12-02",
        start_time="10:00", end_time="11:00", description="Existing event",
        faculty_user_id=3002, created_by_user_id=club.coordinator_user_id,
    )
    ClubSession.objects.create(
        club=club, venue="Auditorium", date="2026-12-03",
        start_time="10:00", end_time="11:00", description="Existing session",
        created_by_user_id=club.coordinator_user_id,
    )

    attempts = (
        ("sessions", "2026-12-01", "session"),
        ("events", "2026-12-02", "event"),
        ("events", "2026-12-03", "session"),
    )
    for endpoint, booking_date, existing_type in attempts:
        payload = {
            "venue": "Auditorium",
            "date": booking_date,
            "start_time": "10:30",
            "end_time": "11:30",
            "description": "Overlapping booking",
        }
        if endpoint == "events":
            payload.update({"name": "New event", "faculty_user_id": 3002})
        response = head.post(
            f"{ROOT}/clubs/{club.pk}/{endpoint}",
            payload,
            format="json",
        )
        assert response.status_code == 409, (existing_type, response.content)
        assert response.json()["error"]["code"] == "venue_conflict"

    assert ClubSession.objects.count() == 2
    assert ClubEvent.objects.count() == 1


@override_settings(GYMKHANA_VENUES=("Auditorium", "Gym"))
def test_gym_008_nonmatching_venue_date_or_time_bookings_are_accepted(stub_iam):
    """test_id=GYM-008; source_id=BR-GYM-006"""
    club = _club()
    _person(3002, "faculty")
    ClubSession.objects.create(
        club=club, venue="Auditorium", date="2026-12-01",
        start_time="10:00", end_time="11:00", description="Existing",
        created_by_user_id=club.coordinator_user_id,
    )
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    requests = (
        {
            "venue": "Gym", "date": "2026-12-01",
            "start_time": "10:30", "end_time": "11:30",
            "description": "Different venue",
        },
        {
            "venue": "Auditorium", "date": "2026-12-02",
            "start_time": "10:30", "end_time": "11:30",
            "description": "Different date",
        },
        {
            "venue": "Auditorium", "date": "2026-12-01",
            "start_time": "11:00", "end_time": "12:00",
            "description": "Adjacent slot",
        },
    )
    for payload in requests:
        response = head.post(
            f"{ROOT}/clubs/{club.pk}/sessions", payload, format="json",
        )
        assert response.status_code == 201, response.content

    assert ClubSession.objects.filter(club=club).count() == 4


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_gym_009_sessions_and_events_require_configured_venues(stub_iam):
    """test_id=GYM-009; source_id=BR-GYM-020"""
    club = _club()
    _person(3002, "faculty")
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    valid_session = head.post(
        f"{ROOT}/clubs/{club.pk}/sessions",
        {
            "venue": "Auditorium", "date": "2026-12-01",
            "start_time": "09:00", "end_time": "10:00", "description": "Session",
        },
        format="json",
    )
    assert valid_session.status_code == 201, valid_session.content
    invalid_session = head.post(
        f"{ROOT}/clubs/{club.pk}/sessions",
        {
            "venue": "Unconfigured", "date": "2026-12-02",
            "start_time": "09:00", "end_time": "10:00", "description": "Session",
        },
        format="json",
    )
    assert invalid_session.status_code == 400

    valid_event = head.post(
        f"{ROOT}/clubs/{club.pk}/events",
        {
            "name": "Event", "faculty_user_id": 3002, "venue": "Auditorium",
            "date": "2026-12-03", "start_time": "09:00", "end_time": "10:00",
            "description": "Event",
        },
        format="json",
    )
    assert valid_event.status_code == 201, valid_event.content
    invalid_event = head.post(
        f"{ROOT}/clubs/{club.pk}/events",
        {
            "name": "Event", "faculty_user_id": 3002, "venue": "Unconfigured",
            "date": "2026-12-04", "start_time": "09:00", "end_time": "10:00",
            "description": "Event",
        },
        format="json",
    )
    assert invalid_event.status_code == 400
    assert ClubSession.objects.count() == 1
    assert ClubEvent.objects.count() == 1


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_gym_010_new_sessions_and_events_enqueue_notifications(stub_iam):
    """test_id=GYM-010; source_id=Problem Statement §4.1 In Scope"""
    club = _club()
    _person(4101)
    MembershipApplication.objects.create(
        club=club,
        student_user_id=4101,
        description="Member",
        status=MembershipApplication.Status.CONFIRMED,
    )
    _person(3002, "faculty")
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    session = head.post(
        f"{ROOT}/clubs/{club.pk}/sessions",
        {
            "venue": "Auditorium", "date": "2026-12-01",
            "start_time": "09:00", "end_time": "10:00", "description": "Session",
        },
        format="json",
    )
    event = head.post(
        f"{ROOT}/clubs/{club.pk}/events",
        {
            "name": "Event", "faculty_user_id": 3002, "venue": "Auditorium",
            "date": "2026-12-02", "start_time": "09:00", "end_time": "10:00",
            "description": "Event",
        },
        format="json",
    )

    assert session.status_code == 201, session.content
    assert event.status_code == 201, event.content
    assert NotificationOutbox.objects.filter(
        topic="session.booked", recipient_user_id=4101,
    ).exists()
    assert NotificationOutbox.objects.filter(
        topic="event.booked", recipient_user_id=4101,
    ).exists()


def test_gym_011_membership_requires_confirmed_club(stub_iam):
    """test_id=GYM-011; source_id=BR-GYM-007"""
    open_club = _club(name="Open Club", status=Club.Status.OPEN)
    confirmed_club = _club(name="Confirmed Club", status=Club.Status.CONFIRMED)
    student = _client(stub_iam, user_id=4101)

    confirmed_response = student.post(
        f"{ROOT}/clubs/{confirmed_club.pk}/memberships",
        {"description": "Interested"},
        format="json",
    )
    open_response = student.post(
        f"{ROOT}/clubs/{open_club.pk}/memberships",
        {"description": "Interested"},
        format="json",
    )

    assert confirmed_response.status_code == 201, confirmed_response.content
    assert open_response.status_code == 409
    assert MembershipApplication.objects.filter(club=confirmed_club).count() == 1
    assert not MembershipApplication.objects.filter(club=open_club).exists()


def test_gym_012_different_club_applications_allowed_duplicate_rejected(stub_iam):
    """test_id=GYM-012; source_id=BR-GYM-008; BR-GYM-009"""
    first = _club(name="Robotics")
    second = _club(name="Aero")
    student = _client(stub_iam, user_id=4101)

    first_response = student.post(
        f"{ROOT}/clubs/{first.pk}/memberships",
        {"description": "Robotics"},
        format="json",
    )
    second_response = student.post(
        f"{ROOT}/clubs/{second.pk}/memberships",
        {"description": "Aero"},
        format="json",
    )
    duplicate_response = student.post(
        f"{ROOT}/clubs/{first.pk}/memberships",
        {"description": "Duplicate"},
        format="json",
    )

    assert first_response.status_code == 201, first_response.content
    assert second_response.status_code == 201, second_response.content
    assert duplicate_response.status_code == 409
    assert MembershipApplication.objects.filter(student_user_id=4101).count() == 2
    original = MembershipApplication.objects.get(club=first, student_user_id=4101)
    assert original.description == "Robotics"
    assert original.status == MembershipApplication.Status.OPEN


def test_gym_013_only_current_club_heads_can_perform_club_head_operations(stub_iam):
    """test_id=GYM-013; source_id=BR-GYM-010"""
    club = _club()
    first = MembershipApplication.objects.create(
        club=club, student_user_id=4101, description="First",
    )
    second = MembershipApplication.objects.create(
        club=club, student_user_id=4102, description="Second",
    )
    third = MembershipApplication.objects.create(
        club=club, student_user_id=4103, description="Third",
    )

    coordinator = _client(stub_iam, user_id=club.coordinator_user_id)
    first_response = coordinator.post(
        f"{ROOT}/clubs/{club.pk}/memberships/{first.pk}/approve",
        {}, format="json",
    )
    co_coordinator = _client(stub_iam, user_id=club.co_coordinator_user_id)
    second_response = co_coordinator.post(
        f"{ROOT}/clubs/{club.pk}/memberships/{second.pk}/approve",
        {}, format="json",
    )
    other_user = _client(stub_iam, user_id=4104)
    denied_response = other_user.post(
        f"{ROOT}/clubs/{club.pk}/memberships/{third.pk}/approve",
        {}, format="json",
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert denied_response.status_code == 403
    first.refresh_from_db()
    second.refresh_from_db()
    third.refresh_from_db()
    assert first.status == MembershipApplication.Status.CONFIRMED
    assert second.status == MembershipApplication.Status.CONFIRMED
    assert third.status == MembershipApplication.Status.OPEN


def test_gym_014_membership_approval_confirms_and_retains_optional_remarks(stub_iam):
    """test_id=GYM-014; source_id=BR-GYM-011"""
    club = _club()
    with_remarks = MembershipApplication.objects.create(
        club=club, student_user_id=4101, description="First",
    )
    without_remarks = MembershipApplication.objects.create(
        club=club, student_user_id=4102, description="Second",
    )
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    first = head.post(
        f"{ROOT}/clubs/{club.pk}/memberships/{with_remarks.pk}/approve",
        {"remarks": "Welcome"},
        format="json",
    )
    second = head.post(
        f"{ROOT}/clubs/{club.pk}/memberships/{without_remarks.pk}/approve",
        {},
        format="json",
    )

    assert first.status_code == 200
    assert second.status_code == 200
    with_remarks.refresh_from_db()
    without_remarks.refresh_from_db()
    assert with_remarks.status == MembershipApplication.Status.CONFIRMED
    assert with_remarks.remarks == "Welcome"
    assert without_remarks.status == MembershipApplication.Status.CONFIRMED
    assert without_remarks.remarks == ""


def test_gym_015_poll_requires_at_least_two_choices(stub_iam):
    """test_id=GYM-015; source_id=BR-GYM-012"""
    club = _club()
    _person(4101)
    head = _client(stub_iam, user_id=club.coordinator_user_id)
    common = {
        "club_id": club.pk,
        "title": "Choose a project",
        "expires_at": "2030-01-01T10:00:00+05:30",
        "target_groups": [{"batch_year": 2024, "discipline": "CSE"}],
    }

    too_few = head.post(
        f"{ROOT}/polls", {**common, "choices": ["One"]}, format="json",
    )
    assert too_few.status_code == 400
    assert not VotingPoll.objects.exists()

    exactly_two = head.post(
        f"{ROOT}/polls", {**common, "choices": ["One", "Two"]}, format="json",
    )
    assert exactly_two.status_code == 201, exactly_two.content
    assert VotingPoll.objects.get().choices.count() == 2


def test_gym_016_poll_notifications_and_access_follow_selected_groups(stub_iam):
    """test_id=GYM-016; source_id=BR-GYM-013"""
    club = _club()
    _person(4101, batch_year=2024, discipline="CSE")
    _person(4102, batch_year=2024, discipline="CSE")
    _person(4103, batch_year=2024, discipline="ECE")
    _person(4104, batch_year=2025, discipline="CSE")
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    created = head.post(
        f"{ROOT}/polls",
        {
            "club_id": club.pk,
            "title": "CSE poll",
            "expires_at": "2030-01-01T10:00:00+05:30",
            "choices": ["One", "Two"],
            "target_groups": [{"batch_year": 2024, "discipline": "CSE"}],
        },
        format="json",
    )

    assert created.status_code == 201, created.content
    assert set(NotificationOutbox.objects.filter(
        topic="poll.created",
    ).values_list("recipient_user_id", flat=True)) == {4101, 4102}
    for user_id, expected_count in ((4101, 1), (4103, 0), (4104, 0)):
        student = _client(stub_iam, user_id=user_id)
        listing = student.get(f"{ROOT}/polls")
        assert listing.status_code == 200
        assert len(listing.json()["results"]) == expected_count


def test_gym_017_all_branches_target_includes_batch_students(stub_iam):
    """test_id=GYM-017; source_id=BR-GYM-013 Exceptions/Exclusions"""
    club = _club()
    _person(4101, batch_year=2024, discipline="CSE")
    _person(4102, batch_year=2024, discipline="ECE")
    _person(4103, batch_year=2025, discipline="CSE")
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/polls",
        {
            "club_id": club.pk,
            "title": "All branches",
            "expires_at": "2030-01-01T10:00:00+05:30",
            "choices": ["One", "Two"],
            "target_groups": [{"batch_year": 2024, "discipline": "*"}],
        },
        format="json",
    )

    assert response.status_code == 201, response.content
    assert set(NotificationOutbox.objects.filter(
        topic="poll.created",
    ).values_list("recipient_user_id", flat=True)) == {4101, 4102}
    for user_id, expected_count in ((4101, 1), (4102, 1), (4103, 0)):
        student = _client(stub_iam, user_id=user_id)
        listing = student.get(f"{ROOT}/polls")
        assert len(listing.json()["results"]) == expected_count


def test_gym_018_participation_requires_active_unexpired_poll_and_audience(stub_iam):
    """test_id=GYM-018; source_id=BR-GYM-014"""
    club = _club()
    _person(4101, batch_year=2024, discipline="CSE")
    _person(4102, batch_year=2024, discipline="ECE")
    eligible = _create_poll(club)
    inactive = _create_poll(club, active=False)
    expired = _create_poll(
        club,
        expires_at=timezone.now() - timedelta(days=1),
    )
    outside_audience = _create_poll(club, target_branch="ECE")
    voter = _client(stub_iam, user_id=4101)

    available = voter.get(f"{ROOT}/polls")
    assert available.status_code == 200
    assert [row["id"] for row in available.json()["results"]] == [eligible.pk]

    for poll in (eligible, inactive, expired, outside_audience):
        choice = poll.choices.first()
        response = voter.post(
            f"{ROOT}/polls/{poll.pk}/vote",
            {"choice_id": choice.pk},
            format="json",
        )
        if poll == eligible:
            assert response.status_code == 200
        else:
            assert response.status_code == 409
    assert PollVote.objects.filter(poll=eligible, student_user_id=4101).count() == 1
    assert PollVote.objects.exclude(poll=eligible).count() == 0


def test_gym_019_student_can_vote_only_once_per_poll(stub_iam):
    """test_id=GYM-019; source_id=BR-GYM-015"""
    club = _club()
    _person(4101)
    poll = _create_poll(club)
    choice = poll.choices.first()
    voter = _client(stub_iam, user_id=4101)

    first = voter.post(
        f"{ROOT}/polls/{poll.pk}/vote", {"choice_id": choice.pk}, format="json",
    )
    second = voter.post(
        f"{ROOT}/polls/{poll.pk}/vote", {"choice_id": choice.pk}, format="json",
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert PollVote.objects.filter(poll=poll, student_user_id=4101).count() == 1


def test_gym_020_zero_amount_budget_with_file_is_retained(stub_iam):
    """test_id=GYM-020; source_id=BR-GYM-017; BR-GYM-018"""
    club = _club()
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/budgets",
        {
            "amount": "0",
            "purpose": "Parts",
            "description": "Prototype materials",
            "supporting_file": SimpleUploadedFile("quote.txt", b"vendor quote"),
        },
        format="multipart",
    )

    assert response.status_code == 201, response.content
    request = BudgetRequest.objects.get(club=club)
    assert request.amount == 0
    assert request.supporting_file.storage.exists(request.supporting_file.name)


def test_gym_021_negative_budget_amount_is_rejected(stub_iam):
    """test_id=GYM-021; source_id=BR-GYM-017"""
    club = _club()
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/budgets",
        {
            "amount": "-1",
            "purpose": "Parts",
            "description": "Prototype materials",
            "supporting_file": SimpleUploadedFile("quote.txt", b"vendor quote"),
        },
        format="multipart",
    )

    assert response.status_code == 400
    assert not BudgetRequest.objects.filter(club=club).exists()


def test_gym_022_budget_request_requires_supporting_file(stub_iam):
    """test_id=GYM-022; source_id=BR-GYM-018"""
    club = _club()
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/budgets",
        {"amount": "0", "purpose": "Parts", "description": "No file"},
        format="multipart",
    )

    assert response.status_code == 400
    assert not BudgetRequest.objects.filter(club=club).exists()


def test_gym_023_invalid_faculty_cannot_be_used_for_event(stub_iam):
    """test_id=GYM-023; source_id=BR-GYM-002"""
    club = _club()
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/events",
        {
            "name": "Talk",
            "faculty_user_id": 3999,
            "venue": "Auditorium",
            "date": "2026-12-01",
            "start_time": "10:00",
            "end_time": "11:00",
            "description": "Guest talk",
        },
        format="json",
    )

    assert response.status_code == 409
    assert not ClubEvent.objects.filter(club=club).exists()


def test_gym_024_report_file_is_stored_and_available_to_assigned_councillor(stub_iam):
    """test_id=GYM-024; source_id=BR-GYM-019; BR-GYM-021; Problem Statement §3.5 Event Reporting"""
    club = _club()
    _person(4101)
    head = _client(stub_iam, user_id=club.coordinator_user_id)
    submitted = head.post(
        f"{ROOT}/clubs/{club.pk}/reports",
        _report_payload(),
        format="multipart",
    )

    assert submitted.status_code == 201, submitted.content
    report = ClubEventReport.objects.get(pk=submitted.json()["id"])
    assert report.report_file.storage.exists(report.report_file.name)
    faculty = _client(
        stub_iam,
        user_id=club.faculty_councillor_user_id,
        kind="faculty",
        role="faculty",
        permissions=FACULTY,
    )
    listing = faculty.get(f"{ROOT}/reports/assigned")
    assert listing.status_code == 200
    assert any(row["id"] == report.pk for row in listing.json()["results"])
    file_response = faculty.get(submitted.json()["download_url"])
    assert file_response.status_code == 200
    assert b"event report" in b"".join(file_response.streaming_content)


def test_gym_025_event_report_requires_report_details_file(stub_iam):
    """test_id=GYM-025; source_id=BR-GYM-019"""
    club = _club()
    _person(4101)
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/reports",
        _report_payload(include_file=False),
        format="multipart",
    )

    assert response.status_code == 400
    assert not ClubEventReport.objects.filter(club=club).exists()


def test_gym_026_only_assigned_faculty_can_review_club_report(stub_iam):
    """test_id=GYM-026; source_id=BR-GYM-021"""
    club = _club()
    _person(4101)
    _person(3002, "faculty")
    head = _client(stub_iam, user_id=club.coordinator_user_id)
    submitted = head.post(
        f"{ROOT}/clubs/{club.pk}/reports",
        _report_payload(),
        format="multipart",
    )
    assert submitted.status_code == 201, submitted.content
    other_faculty = _client(
        stub_iam, user_id=3002, kind="faculty", role="faculty", permissions=FACULTY,
    )

    listing = other_faculty.get(f"{ROOT}/reports/assigned")
    file_response = other_faculty.get(submitted.json()["download_url"])

    assert listing.status_code == 200
    assert not listing.json()["results"]
    assert file_response.status_code == 403
