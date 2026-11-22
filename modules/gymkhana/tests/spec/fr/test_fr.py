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
    Club,
    ClubEvent,
    ClubEventReport,
    ClubSession,
    MembershipApplication,
    NotificationOutbox,
    PollChoice,
    PollTargetGroup,
    VotingPoll,
)

pytestmark = pytest.mark.django_db

ROOT = "/api/v1/gymkhana"
ADMIN = tuple(registry.ROLE_GRANTS["Student Admin"])
FACULTY = tuple(registry.ROLE_GRANTS["faculty"])


@pytest.fixture(autouse=True)
def isolate_uploads(monkeypatch, tmp_path):
    from modules.gymkhana.models import _storage

    monkeypatch.setattr(_storage, "_location", str(tmp_path))


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
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


def _person(user_id, kind="student", *, batch_year=2024, discipline="CSE"):
    user_ref = apps.get_model("directory", "UserRef")
    return user_ref.objects.create(
        user_id=user_id,
        username=f"fr-{user_id}",
        display_name=f"FR Person {user_id}",
        kind=kind,
        batch_year=batch_year if kind == "student" else None,
        discipline=discipline if kind == "student" else "",
    )


def _club(
    *,
    name="Robotics",
    status=Club.Status.CONFIRMED,
    coordinator_user_id=2001,
    co_coordinator_user_id=2002,
    faculty_councillor_user_id=3001,
):
    return Club.objects.create(
        name=name,
        category=Club.Category.TECHNICAL,
        coordinator_user_id=coordinator_user_id,
        co_coordinator_user_id=co_coordinator_user_id,
        faculty_councillor_user_id=faculty_councillor_user_id,
        description="Build things",
        status=status,
    )


def _club_data(**changes):
    return {
        "name": "Robotics",
        "category": "Technical",
        "coordinator_user_id": 2001,
        "co_coordinator_user_id": 2002,
        "faculty_councillor_user_id": 3001,
        "description": "Build things",
        **changes,
    }


def _poll(club, *, expires_at=None, target_batch=2024, target_branch="CSE"):
    poll = VotingPoll.objects.create(
        club=club,
        title="Choose a project",
        description="Vote once",
        expires_at=expires_at or timezone.now() + timedelta(days=30),
        created_by_user_id=club.coordinator_user_id,
    )
    choices = PollChoice.objects.bulk_create([
        PollChoice(poll=poll, text="Rover"),
        PollChoice(poll=poll, text="Drone"),
    ])
    PollTargetGroup.objects.create(
        poll=poll, batch_year=target_batch, discipline=target_branch,
    )
    return poll, choices


def _report_data(**changes):
    return {
        "student_incharge_user_id": 4101,
        "event_name": "Robot showcase",
        "event_at": (timezone.now() - timedelta(days=1)).isoformat(),
        "description": "Event summary",
        "report_file": SimpleUploadedFile("report.txt", b"event report"),
        **changes,
    }


def test_gym_001_create_club_with_valid_assignments(stub_iam):
    """test_id=GYM-001; source_id=AFR-GYM-001; AFR-GYM-005"""
    _person(2001)
    _person(2002)
    _person(3001, "faculty")
    admin = _client(stub_iam, user_id=9001, role="Student Admin", permissions=ADMIN)

    response = admin.post(f"{ROOT}/clubs", _club_data(), format="json")

    assert response.status_code == 201
    assert response.json()["name"] == "Robotics"
    assert response.json()["category"] == "Technical"
    assert response.json()["coordinator_user_id"] == 2001
    assert response.json()["co_coordinator_user_id"] == 2002
    assert response.json()["faculty_councillor_user_id"] == 3001
    assert response.json()["description"] == "Build things"
    assert response.json()["status"] == Club.Status.OPEN


def test_gym_002_invalid_club_assignments_and_category_are_rejected(stub_iam):
    """test_id=GYM-002; source_id=AFR-GYM-002; AFR-GYM-003; AFR-GYM-004"""
    _person(2001)
    _person(2002)
    _person(3001, "faculty")
    admin = _client(stub_iam, user_id=9001, role="Student Admin", permissions=ADMIN)
    invalid_variations = (
        _club_data(name="Invalid Coordinator", coordinator_user_id=2991),
        _club_data(name="Invalid Co-coordinator", co_coordinator_user_id=2992),
        _club_data(name="Invalid Councillor", faculty_councillor_user_id=2001),
        _club_data(name="Invalid Category", category="Other"),
    )

    for data in invalid_variations:
        response = admin.post(f"{ROOT}/clubs", data, format="json")
        assert response.status_code in (400, 409)
    assert Club.objects.count() == 0


def test_gym_003_student_admin_confirms_open_club(stub_iam):
    """test_id=GYM-003; source_id=AFR-GYM-006"""
    club = _club(status=Club.Status.OPEN)
    admin = _client(stub_iam, user_id=9001, role="Student Admin", permissions=ADMIN)

    response = admin.post(f"{ROOT}/clubs/{club.pk}/approve")

    assert response.status_code == 200
    assert response.json()["status"] == Club.Status.CONFIRMED
    club.refresh_from_db()
    assert club.status == Club.Status.CONFIRMED


def test_gym_004_club_establishment_and_confirmation_are_student_admin_only(stub_iam):
    """test_id=GYM-004; source_id=CFR-GYM-001"""
    club = _club(status=Club.Status.OPEN)
    _person(2001)
    _person(2002)
    _person(3001, "faculty")
    student = _client(stub_iam, user_id=9001)

    create_response = student.post(f"{ROOT}/clubs", _club_data(), format="json")
    approve_response = student.post(f"{ROOT}/clubs/{club.pk}/approve")

    assert create_response.status_code == 403
    assert approve_response.status_code == 403
    assert Club.objects.count() == 1
    club.refresh_from_db()
    assert club.status == Club.Status.OPEN


def test_gym_005_change_leadership_to_valid_students(stub_iam):
    """test_id=GYM-005; source_id=AFR-GYM-007; AFR-GYM-009"""
    club = _club()
    _person(2101)
    _person(2102)
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/leadership",
        {"coordinator_user_id": 2101, "co_coordinator_user_id": 2102},
        format="json",
    )

    assert response.status_code == 200
    club.refresh_from_db()
    assert club.coordinator_user_id == 2101
    assert club.co_coordinator_user_id == 2102


def test_gym_006_invalid_leadership_replacements_are_rejected(stub_iam):
    """test_id=GYM-006; source_id=AFR-GYM-008"""
    club = _club()
    _person(2101)
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    for coordinator, co_coordinator in ((2991, 2002), (2001, 2992)):
        response = head.post(
            f"{ROOT}/clubs/{club.pk}/leadership",
            {
                "coordinator_user_id": coordinator,
                "co_coordinator_user_id": co_coordinator,
            },
            format="json",
        )
        assert response.status_code == 409
        club.refresh_from_db()
        assert (club.coordinator_user_id, club.co_coordinator_user_id) == (2001, 2002)


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_gym_007_book_session_and_notify_intended_students(stub_iam):
    """test_id=GYM-007; source_id=AFR-GYM-010; AFR-GYM-013"""
    club = _club()
    MembershipApplication.objects.create(
        club=club, student_user_id=4101, description="Member",
        status=MembershipApplication.Status.CONFIRMED,
    )
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/sessions",
        {
            "venue": "Auditorium",
            "date": "2027-01-15",
            "start_time": "10:00",
            "end_time": "11:00",
            "description": "Build session",
        },
        format="json",
    )

    assert response.status_code == 201
    assert ClubSession.objects.filter(pk=response.json()["id"]).exists()
    assert NotificationOutbox.objects.filter(
        topic="session.booked", recipient_user_id=4101,
    ).exists()


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_gym_008_reject_bookings_with_invalid_time_ranges(stub_iam):
    """test_id=GYM-008; source_id=AFR-GYM-011"""
    club = _club()
    _person(3002, "faculty")
    head = _client(stub_iam, user_id=club.coordinator_user_id)
    session = {
        "venue": "Auditorium",
        "date": "2027-01-15",
        "description": "Invalid time range",
    }
    event = {
        "name": "Robot showcase",
        "faculty_user_id": 3002,
        "venue": "Auditorium",
        "date": "2027-01-15",
        "description": "Invalid time range",
    }

    for start, end in (("10:00", "10:00"), ("11:00", "10:00")):
        session_response = head.post(
            f"{ROOT}/clubs/{club.pk}/sessions",
            session | {"start_time": start, "end_time": end},
            format="json",
        )
        event_response = head.post(
            f"{ROOT}/clubs/{club.pk}/events",
            event | {"start_time": start, "end_time": end},
            format="json",
        )
        assert session_response.status_code == 400
        assert event_response.status_code == 400

    assert ClubSession.objects.count() == 0
    assert ClubEvent.objects.count() == 0


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_gym_009_prevent_overlapping_bookings_across_session_and_event_types(stub_iam):
    """test_id=GYM-009; source_id=AFR-GYM-012; Problem Statement §8"""
    club = _club()
    _person(3002, "faculty")
    head = _client(stub_iam, user_id=club.coordinator_user_id)
    existing_session = {
        "venue": "Auditorium", "date": "2027-01-15",
        "start_time": "10:00", "end_time": "11:00",
        "description": "Existing session",
    }
    existing_event = {
        "name": "Existing event", "venue": "Auditorium", "date": "2027-01-15",
        "start_time": "10:00", "end_time": "11:00",
        "description": "Existing event", "faculty_user_id": 3002,
        "created_by_user_id": club.coordinator_user_id,
    }

    ClubSession.objects.create(club=club, created_by_user_id=2001, **existing_session)
    ClubEvent.objects.create(club=club, **(existing_event | {"date": "2027-01-16"}))
    ClubSession.objects.create(
        club=club, created_by_user_id=2001,
        **(existing_session | {"date": "2027-01-17"}),
    )
    ClubEvent.objects.create(club=club, **(existing_event | {"date": "2027-01-18"}))

    attempts = (
        (
            "sessions",
            "2027-01-15",
            {"description": "Session against session"},
        ),
        (
            "events",
            "2027-01-16",
            {"name": "Event against event", "faculty_user_id": 3002},
        ),
        (
            "sessions",
            "2027-01-17",
            {"description": "Session against event"},
        ),
        (
            "events",
            "2027-01-18",
            {"name": "Event against session", "faculty_user_id": 3002},
        ),
    )
    for endpoint, booking_date, details in attempts:
        payload = {
            **details,
            "venue": "Auditorium",
            "date": booking_date,
            "start_time": "10:30",
            "end_time": "11:30",
            "description": details.get("description", "Overlapping event"),
        }
        response = head.post(
            f"{ROOT}/clubs/{club.pk}/{endpoint}",
            payload,
            format="json",
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "venue_conflict"

    assert ClubSession.objects.count() == 2
    assert ClubEvent.objects.count() == 2


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_gym_010_book_event_and_notify_intended_students(stub_iam):
    """test_id=GYM-010; source_id=AFR-GYM-014; AFR-GYM-015"""
    club = _club()
    _person(3002, "faculty")
    MembershipApplication.objects.create(
        club=club, student_user_id=4101, description="Member",
        status=MembershipApplication.Status.CONFIRMED,
    )
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/events",
        {
            "name": "Robot showcase",
            "faculty_user_id": 3002,
            "venue": "Auditorium",
            "date": "2027-01-15",
            "start_time": "10:00",
            "end_time": "11:00",
            "description": "Showcase",
        },
        format="json",
    )

    assert response.status_code == 201
    assert ClubEvent.objects.filter(pk=response.json()["id"]).exists()
    assert NotificationOutbox.objects.filter(
        topic="event.booked", recipient_user_id=4101,
    ).exists()


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_gym_011_reject_event_with_invalid_faculty_context(stub_iam):
    """test_id=GYM-011; source_id=AFR-GYM-003; CFR-GYM-003"""
    club = _club()
    _person(3002, "student")
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/events",
        {
            "name": "Robot showcase",
            "faculty_user_id": 3002,
            "venue": "Auditorium",
            "date": "2027-01-15",
            "start_time": "10:00",
            "end_time": "11:00",
            "description": "Showcase",
        },
        format="json",
    )

    assert response.status_code == 409
    assert ClubEvent.objects.count() == 0


def test_gym_012_student_applies_to_multiple_confirmed_clubs(stub_iam):
    """test_id=GYM-012; source_id=AFR-GYM-016; AFR-GYM-017; AFR-GYM-019"""
    first = _club(name="Robotics")
    second = _club(name="Astronomy")
    student = _client(stub_iam, user_id=4101)

    first_response = student.post(
        f"{ROOT}/clubs/{first.pk}/memberships",
        {"description": "I build robots"},
        format="json",
    )
    second_response = student.post(
        f"{ROOT}/clubs/{second.pk}/memberships",
        {"description": "I enjoy astronomy"},
        format="json",
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    applications = MembershipApplication.objects.filter(student_user_id=4101)
    assert applications.count() == 2
    assert set(applications.values_list("club_id", "status")) == {
        (first.pk, MembershipApplication.Status.OPEN),
        (second.pk, MembershipApplication.Status.OPEN),
    }


def test_gym_013_prevent_duplicate_membership_application(stub_iam):
    """test_id=GYM-013; source_id=AFR-GYM-018"""
    club = _club()
    MembershipApplication.objects.create(
        club=club, student_user_id=4101, description="Original application",
    )
    student = _client(stub_iam, user_id=4101)

    response = student.post(
        f"{ROOT}/clubs/{club.pk}/memberships",
        {"description": "Duplicate application"},
        format="json",
    )

    assert response.status_code == 409
    assert MembershipApplication.objects.filter(
        club=club, student_user_id=4101,
    ).count() == 1


def test_gym_014_membership_application_requires_confirmed_club(stub_iam):
    """test_id=GYM-014; source_id=Problem Statement §6 — membership applications are allowed only for confirmed clubs"""
    club = _club(status=Club.Status.OPEN)
    student = _client(stub_iam, user_id=4101)

    response = student.post(
        f"{ROOT}/clubs/{club.pk}/memberships",
        {"description": "I build robots"},
        format="json",
    )

    assert response.status_code == 409
    assert MembershipApplication.objects.filter(club=club).count() == 0


def test_gym_015_applicable_club_head_accesses_and_approves_application(stub_iam):
    """test_id=GYM-015; source_id=AFR-GYM-020; AFR-GYM-021; AFR-GYM-022"""
    club = _club()
    application = MembershipApplication.objects.create(
        club=club, student_user_id=4101, description="I build things",
    )
    head = _client(stub_iam, user_id=club.coordinator_user_id)
    pending = head.get(f"{ROOT}/clubs/{club.pk}/memberships")

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/memberships/{application.pk}/approve",
        {},
        format="json",
    )

    assert pending.status_code == 200
    assert any(row["id"] == application.pk for row in pending.json()["results"])
    assert response.status_code == 200
    application.refresh_from_db()
    assert application.status == MembershipApplication.Status.CONFIRMED


def test_gym_016_other_club_head_cannot_approve_membership(stub_iam):
    """test_id=GYM-016; source_id=AFR-GYM-021"""
    club = _club(name="Robotics", coordinator_user_id=2001, co_coordinator_user_id=2002)
    other_club = _club(name="Astronomy", coordinator_user_id=2003, co_coordinator_user_id=2004)
    application = MembershipApplication.objects.create(
        club=club, student_user_id=4101, description="I build things",
    )
    other_head = _client(stub_iam, user_id=other_club.coordinator_user_id)

    response = other_head.post(
        f"{ROOT}/clubs/{club.pk}/memberships/{application.pk}/approve",
        {},
        format="json",
    )

    assert response.status_code == 403
    application.refresh_from_db()
    assert application.status == MembershipApplication.Status.OPEN


def test_gym_017_create_active_targeted_poll_and_notify_students(stub_iam):
    """test_id=GYM-017; source_id=AFR-GYM-023; AFR-GYM-025"""
    club = _club()
    _person(4101, batch_year=2024, discipline="CSE")
    _person(4102, batch_year=2024, discipline="ECE")
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/polls",
        {
            "club_id": club.pk,
            "title": "Choose a project",
            "description": "Vote once",
            "expires_at": (timezone.now() + timedelta(days=30)).isoformat(),
            "choices": ["Rover", "Drone"],
            "target_groups": [
                {"batch_year": 2024, "discipline": "CSE"},
                {"batch_year": 2024, "discipline": "ECE"},
            ],
        },
        format="json",
    )

    assert response.status_code == 201
    poll = VotingPoll.objects.get(pk=response.json()["id"])
    assert poll.is_active
    assert poll.expires_at > timezone.now()
    assert set(poll.target_groups.values_list("batch_year", "discipline")) == {
        (2024, "CSE"), (2024, "ECE"),
    }
    assert set(NotificationOutbox.objects.filter(
        topic="poll.created",
    ).values_list("recipient_user_id", flat=True)) == {4101, 4102}


def test_gym_018_poll_requires_at_least_two_choices(stub_iam):
    """test_id=GYM-018; source_id=AFR-GYM-024"""
    club = _club()
    _person(4101, batch_year=2024, discipline="CSE")
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/polls",
        {
            "club_id": club.pk,
            "title": "Choose a project",
            "description": "One choice",
            "expires_at": (timezone.now() + timedelta(days=30)).isoformat(),
            "choices": ["Rover"],
            "target_groups": [{"batch_year": 2024, "discipline": "CSE"}],
        },
        format="json",
    )

    assert response.status_code == 400
    assert VotingPoll.objects.count() == 0


def test_gym_019_targeted_student_can_access_active_poll_and_choices(stub_iam):
    """test_id=GYM-019; source_id=AFR-GYM-026"""
    club = _club()
    _person(4101, batch_year=2024, discipline="CSE")
    poll, choices = _poll(club)
    student = _client(stub_iam, user_id=4101)

    response = student.get(f"{ROOT}/polls")

    assert response.status_code == 200
    result = next(row for row in response.json()["results"] if row["id"] == poll.pk)
    assert {row["id"] for row in result["choices"]} == {choice.pk for choice in choices}


def test_gym_020_non_targeted_student_cannot_access_or_vote_in_poll(stub_iam):
    """test_id=GYM-020; source_id=AFR-GYM-026; AFR-GYM-027"""
    club = _club()
    _person(4101, batch_year=2024, discipline="ECE")
    poll, choices = _poll(club, target_branch="CSE")
    student = _client(stub_iam, user_id=4101)

    listed = student.get(f"{ROOT}/polls")
    vote = student.post(
        f"{ROOT}/polls/{poll.pk}/vote",
        {"choice_id": choices[0].pk},
        format="json",
    )

    assert listed.status_code == 200
    assert all(row["id"] != poll.pk for row in listed.json()["results"])
    assert vote.status_code == 409
    assert poll.votes.count() == 0


def test_gym_021_accept_one_vote_prevent_second_and_update_tally(stub_iam):
    """test_id=GYM-021; source_id=AFR-GYM-027; AFR-GYM-028"""
    club = _club()
    _person(4101, batch_year=2024, discipline="CSE")
    poll, choices = _poll(club)
    student = _client(stub_iam, user_id=4101)

    accepted = student.post(
        f"{ROOT}/polls/{poll.pk}/vote",
        {"choice_id": choices[0].pk},
        format="json",
    )
    rejected = student.post(
        f"{ROOT}/polls/{poll.pk}/vote",
        {"choice_id": choices[1].pk},
        format="json",
    )
    poll_listing = student.get(f"{ROOT}/polls")

    assert accepted.status_code == 200
    assert rejected.status_code == 409
    assert poll.votes.count() == 1
    assert choices[0].votes.count() == 1
    assert choices[1].votes.count() == 0
    result = next(
        row for row in poll_listing.json()["results"] if row["id"] == poll.pk
    )
    assert result["has_voted"] is True
    assert next(row for row in result["choices"] if row["id"] == choices[0].pk)[
        "vote_count"
    ] == 1


def test_gym_022_submit_zero_amount_budget_request_with_file(stub_iam):
    """test_id=GYM-022; source_id=AFR-GYM-029; AFR-GYM-030; AFR-GYM-031"""
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

    assert response.status_code == 201
    assert response.json()["status"] == "open"
    assert club.budget_requests.count() == 1


def test_gym_023_reject_negative_or_fileless_budget_request(stub_iam):
    """test_id=GYM-023; source_id=AFR-GYM-030"""
    club = _club()
    head = _client(stub_iam, user_id=club.coordinator_user_id)
    negative = head.post(
        f"{ROOT}/clubs/{club.pk}/budgets",
        {
            "amount": "-1",
            "purpose": "Parts",
            "description": "Negative amount",
            "supporting_file": SimpleUploadedFile("quote.txt", b"vendor quote"),
        },
        format="multipart",
    )
    missing_file = head.post(
        f"{ROOT}/clubs/{club.pk}/budgets",
        {"amount": "0", "purpose": "Parts", "description": "Missing file"},
        format="multipart",
    )

    assert negative.status_code == 400
    assert missing_file.status_code == 400
    assert club.budget_requests.count() == 0


def test_gym_024_submit_documented_event_report(stub_iam):
    """test_id=GYM-024; source_id=AFR-GYM-032; AFR-GYM-033"""
    club = _club()
    _person(4101)
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/reports",
        _report_data(),
        format="multipart",
    )

    assert response.status_code == 201
    report = ClubEventReport.objects.get(pk=response.json()["id"])
    assert report.club == club
    assert report.student_incharge_user_id == 4101
    assert report.event_name == "Robot showcase"
    assert report.report_file


def test_gym_025_event_report_requires_report_details_file(stub_iam):
    """test_id=GYM-025; source_id=AFR-GYM-033"""
    club = _club()
    _person(4101)
    head = _client(stub_iam, user_id=club.coordinator_user_id)
    data = _report_data()
    data.pop("report_file")

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/reports", data, format="multipart",
    )

    assert response.status_code == 400
    assert club.reports.count() == 0


def test_gym_026_only_assigned_councillor_can_review_event_reports(stub_iam):
    """test_id=GYM-026; source_id=AFR-GYM-034"""
    club = _club()
    _person(4101)
    _person(3002, "faculty")
    head = _client(stub_iam, user_id=club.coordinator_user_id)
    submitted = head.post(
        f"{ROOT}/clubs/{club.pk}/reports",
        _report_data(),
        format="multipart",
    )
    assert submitted.status_code == 201

    assigned = _client(
        stub_iam, user_id=club.faculty_councillor_user_id,
        kind="faculty", role="faculty", permissions=FACULTY,
    )
    assigned_list = assigned.get(f"{ROOT}/reports/assigned")
    assigned_download = assigned.get(submitted.json()["download_url"])

    other_faculty = _client(
        stub_iam, user_id=3002,
        kind="faculty", role="faculty", permissions=FACULTY,
    )
    denied_list = other_faculty.get(f"{ROOT}/reports/assigned")
    denied_download = other_faculty.get(submitted.json()["download_url"])

    assert assigned_list.status_code == 200
    assert any(
        row["id"] == submitted.json()["id"]
        for row in assigned_list.json()["results"]
    )
    assert assigned_download.status_code == 200
    assert b"event report" in b"".join(assigned_download.streaming_content)
    assert denied_list.status_code == 200
    assert all(
        row["id"] != submitted.json()["id"]
        for row in denied_list.json()["results"]
    )
    assert denied_download.status_code == 403
    assert ClubEventReport.objects.count() == 1
