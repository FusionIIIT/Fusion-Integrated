from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
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
    return UserRef.objects.create(
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


def _club_payload(name="Robotics", **overrides):
    return {
        "name": name,
        "category": "Technical",
        "coordinator_user_id": 2001,
        "co_coordinator_user_id": 2002,
        "faculty_councillor_user_id": 3001,
        "description": "Build things",
        **overrides,
    }


def _poll(club, *, expires_at=None, is_active=True, target="CSE"):
    poll = VotingPoll.objects.create(
        club=club,
        title="Choose a project",
        description="Vote once",
        expires_at=expires_at or timezone.now() + timedelta(days=2),
        created_by_user_id=club.coordinator_user_id,
        is_active=is_active,
    )
    choice = PollChoice.objects.create(poll=poll, text="Rover")
    PollChoice.objects.create(poll=poll, text="Drone")
    PollTargetGroup.objects.create(poll=poll, batch_year=2024, discipline=target)
    return poll, choice


def _valid_report_payload():
    return {
        "student_incharge_user_id": 4001,
        "event_name": "Robot showcase",
        "event_at": "2026-11-01T12:00:00+05:30",
        "description": "Summary",
        "report_file": SimpleUploadedFile("report.txt", b"event report"),
    }


def test_tc001_create_club_with_valid_assignments(stub_iam):
    """test_id=TC-001; source_id=UC-GYM-001 Main Success Scenario"""
    _person(2001)
    _person(2002)
    _person(3001, "faculty")
    admin = _client(stub_iam, user_id=9001, role="Student Admin", permissions=ADMIN)

    response = admin.post(f"{ROOT}/clubs", _club_payload(), format="json")

    assert response.status_code == 201, response.content
    assert response.json()["status"] == Club.Status.OPEN


def test_tc002_invalid_leader_can_be_corrected_without_creating_invalid_club(stub_iam):
    """test_id=TC-002; source_id=UC-GYM-001 Alternative Flow"""
    _person(2001)
    _person(2002)
    _person(3001, "faculty")
    admin = _client(stub_iam, user_id=9001, role="Student Admin", permissions=ADMIN)

    invalid = admin.post(
        f"{ROOT}/clubs",
        _club_payload(coordinator_user_id=2999),
        format="json",
    )
    assert invalid.status_code == 409
    assert Club.objects.count() == 0

    corrected = admin.post(f"{ROOT}/clubs", _club_payload(), format="json")
    assert corrected.status_code == 201, corrected.content
    assert Club.objects.count() == 1


def test_tc003_invalid_faculty_can_be_corrected_without_creating_invalid_club(stub_iam):
    """test_id=TC-003; source_id=UC-GYM-001 Alternative Flow"""
    _person(2001)
    _person(2002)
    _person(3002, "faculty")
    admin = _client(stub_iam, user_id=9001, role="Student Admin", permissions=ADMIN)

    invalid = admin.post(
        f"{ROOT}/clubs",
        _club_payload(faculty_councillor_user_id=3999),
        format="json",
    )
    assert invalid.status_code == 409
    assert Club.objects.count() == 0

    corrected = admin.post(
        f"{ROOT}/clubs",
        _club_payload(faculty_councillor_user_id=3002),
        format="json",
    )
    assert corrected.status_code == 201, corrected.content
    assert Club.objects.count() == 1


def test_tc004_accepts_only_specified_club_categories(stub_iam):
    """test_id=TC-004; source_id=Problem Statement §6 Business Constraints — Club category"""
    _person(2001)
    _person(2002)
    _person(3001, "faculty")
    admin = _client(stub_iam, user_id=9001, role="Student Admin", permissions=ADMIN)

    for category in ("Technical", "Sports", "Cultural"):
        response = admin.post(
            f"{ROOT}/clubs",
            _club_payload(name=f"{category} Club", category=category),
            format="json",
        )
        assert response.status_code == 201, response.content
        assert response.json()["category"] == category

    invalid = admin.post(
        f"{ROOT}/clubs",
        _club_payload(name="Other Club", category="Other"),
        format="json",
    )
    assert invalid.status_code == 400
    assert Club.objects.count() == 3


def test_tc006_student_admin_approves_open_club(stub_iam):
    """test_id=TC-006; source_id=UC-GYM-011 Main Success Scenario"""
    club = _club(status=Club.Status.OPEN)
    admin = _client(stub_iam, user_id=9001, role="Student Admin", permissions=ADMIN)

    before = admin.get(f"{ROOT}/clubs")
    assert before.status_code == 200
    listed = next(row for row in before.json()["results"] if row["id"] == club.pk)
    assert listed["name"] == club.name
    assert listed["coordinator_user_id"] == club.coordinator_user_id
    assert listed["co_coordinator_user_id"] == club.co_coordinator_user_id
    assert listed["faculty_councillor_user_id"] == club.faculty_councillor_user_id

    response = admin.post(f"{ROOT}/clubs/{club.pk}/approve")

    assert response.status_code == 200, response.content
    club.refresh_from_db()
    assert club.status == Club.Status.CONFIRMED


def test_tc007_non_open_club_is_not_approved(stub_iam):
    """test_id=TC-007; source_id=UC-GYM-011 Exception Flow"""
    club = _club(status=Club.Status.CONFIRMED)
    admin = _client(stub_iam, user_id=9001, role="Student Admin", permissions=ADMIN)

    response = admin.post(f"{ROOT}/clubs/{club.pk}/approve")

    assert response.status_code == 409
    club.refresh_from_db()
    assert club.status == Club.Status.CONFIRMED


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_tc009_books_session_and_initiates_notification(stub_iam):
    """test_id=TC-009; source_id=UC-GYM-002 Main Success Scenario"""
    club = _club()
    MembershipApplication.objects.create(
        club=club,
        student_user_id=4101,
        description="Member",
        status=MembershipApplication.Status.CONFIRMED,
    )
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    response = client.post(
        f"{ROOT}/clubs/{club.pk}/sessions",
        {
            "venue": "Auditorium",
            "date": "2026-12-01",
            "start_time": "10:00",
            "end_time": "11:00",
            "description": "Weekly session",
        },
        format="json",
    )

    assert response.status_code == 201, response.content
    assert ClubSession.objects.filter(pk=response.json()["id"]).exists()
    assert NotificationOutbox.objects.filter(
        topic="session.booked", recipient_user_id=4101,
    ).exists()


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_tc010_rejects_session_overlapping_existing_session(stub_iam):
    """test_id=TC-010; source_id=UC-GYM-002 Alternative Flow; Problem Statement §6 Business Constraints — Booking overlap"""
    club = _club()
    ClubSession.objects.create(
        club=club, venue="Auditorium", date="2026-12-01",
        start_time="10:00", end_time="11:00", description="Existing",
        created_by_user_id=club.coordinator_user_id,
    )
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    response = client.post(
        f"{ROOT}/clubs/{club.pk}/sessions",
        {
            "venue": "Auditorium", "date": "2026-12-01",
            "start_time": "10:30", "end_time": "11:30", "description": "New",
        },
        format="json",
    )

    assert response.status_code == 409
    assert ClubSession.objects.count() == 1


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_tc011_rejects_session_overlapping_existing_event(stub_iam):
    """test_id=TC-011; source_id=UC-GYM-002 Alternative Flow; Problem Statement §6 Business Constraints — Booking overlap"""
    club = _club()
    ClubEvent.objects.create(
        club=club, name="Existing", venue="Auditorium", date="2026-12-01",
        start_time="10:00", end_time="11:00", description="Existing",
        faculty_user_id=3001, created_by_user_id=club.coordinator_user_id,
    )
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    response = client.post(
        f"{ROOT}/clubs/{club.pk}/sessions",
        {
            "venue": "Auditorium", "date": "2026-12-01",
            "start_time": "10:30", "end_time": "11:30", "description": "New",
        },
        format="json",
    )

    assert response.status_code == 409
    assert ClubSession.objects.count() == 0


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_tc012_rejects_session_with_invalid_venue(stub_iam):
    """test_id=TC-012; source_id=UC-GYM-002 Exception Flow"""
    club = _club()
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    response = client.post(
        f"{ROOT}/clubs/{club.pk}/sessions",
        {
            "venue": "Invalid Venue", "date": "2026-12-01",
            "start_time": "10:00", "end_time": "11:00", "description": "Session",
        },
        format="json",
    )

    assert response.status_code == 400
    assert ClubSession.objects.count() == 0


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_tc013_rejects_session_with_invalid_time_range(stub_iam):
    """test_id=TC-013; source_id=UC-GYM-002 Exception Flow; Problem Statement §6 Business Constraints — Booking time"""
    club = _club()
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    for start_time, end_time in (("10:00", "10:00"), ("11:00", "10:00")):
        response = client.post(
            f"{ROOT}/clubs/{club.pk}/sessions",
            {
                "venue": "Auditorium", "date": "2026-12-01",
                "start_time": start_time, "end_time": end_time,
                "description": "Session",
            },
            format="json",
        )
        assert response.status_code == 400
    assert ClubSession.objects.count() == 0


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_tc014_session_storage_failure_does_not_record_booking(stub_iam, monkeypatch):
    """test_id=TC-014; source_id=UC-GYM-002 Exception Flow"""
    club = _club()
    client = _client(stub_iam, user_id=club.coordinator_user_id)
    storage = ClubSession._meta.get_field("poster").storage

    def fail_save(*args, **kwargs):
        raise OSError("test file storage unavailable")

    monkeypatch.setattr(storage, "save", fail_save)
    client.raise_request_exception = False

    response = client.post(
        f"{ROOT}/clubs/{club.pk}/sessions",
        {
            "venue": "Auditorium",
            "date": "2026-12-01",
            "start_time": "10:00",
            "end_time": "11:00",
            "description": "Session",
            "poster": SimpleUploadedFile("poster.txt", b"poster"),
        },
        format="multipart",
    )

    assert response.status_code >= 400
    assert not ClubSession.objects.exists()
    assert not NotificationOutbox.objects.filter(topic="session.booked").exists()


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_tc016_books_event_and_initiates_notification(stub_iam):
    """test_id=TC-016; source_id=UC-GYM-003 Main Success Scenario"""
    club = _club()
    _person(3002, "faculty")
    MembershipApplication.objects.create(
        club=club,
        student_user_id=4101,
        description="Member",
        status=MembershipApplication.Status.CONFIRMED,
    )
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    response = client.post(
        f"{ROOT}/clubs/{club.pk}/events",
        {
            "name": "Guest talk", "faculty_user_id": 3002,
            "venue": "Auditorium", "date": "2026-12-01",
            "start_time": "10:00", "end_time": "11:00",
            "description": "A guest talk",
        },
        format="json",
    )

    assert response.status_code == 201, response.content
    assert ClubEvent.objects.filter(pk=response.json()["id"]).exists()
    assert NotificationOutbox.objects.filter(
        topic="event.booked", recipient_user_id=4101,
    ).exists()


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_tc017_rejects_event_overlapping_existing_event(stub_iam):
    """test_id=TC-017; source_id=UC-GYM-003 Alternative Flow; Problem Statement §6 Business Constraints — Booking overlap"""
    club = _club()
    _person(3002, "faculty")
    ClubEvent.objects.create(
        club=club, name="Existing", venue="Auditorium", date="2026-12-01",
        start_time="10:00", end_time="11:00", description="Existing",
        faculty_user_id=3001, created_by_user_id=club.coordinator_user_id,
    )
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    response = client.post(
        f"{ROOT}/clubs/{club.pk}/events",
        {
            "name": "New", "faculty_user_id": 3002, "venue": "Auditorium",
            "date": "2026-12-01", "start_time": "10:30", "end_time": "11:30",
            "description": "New event",
        },
        format="json",
    )

    assert response.status_code == 409
    assert ClubEvent.objects.count() == 1


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_tc018_rejects_event_overlapping_existing_session(stub_iam):
    """test_id=TC-018; source_id=UC-GYM-003 Alternative Flow; Problem Statement §6 Business Constraints — Booking overlap"""
    club = _club()
    _person(3002, "faculty")
    ClubSession.objects.create(
        club=club, venue="Auditorium", date="2026-12-01",
        start_time="10:00", end_time="11:00", description="Existing",
        created_by_user_id=club.coordinator_user_id,
    )
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    response = client.post(
        f"{ROOT}/clubs/{club.pk}/events",
        {
            "name": "New", "faculty_user_id": 3002, "venue": "Auditorium",
            "date": "2026-12-01", "start_time": "10:30", "end_time": "11:30",
            "description": "New event",
        },
        format="json",
    )

    assert response.status_code == 409
    assert ClubEvent.objects.count() == 0


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_tc019_rejects_event_with_invalid_venue(stub_iam):
    """test_id=TC-019; source_id=UC-GYM-003 Exception Flow"""
    club = _club()
    _person(3002, "faculty")
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    response = client.post(
        f"{ROOT}/clubs/{club.pk}/events",
        {
            "name": "Talk", "faculty_user_id": 3002, "venue": "Invalid Venue",
            "date": "2026-12-01", "start_time": "10:00", "end_time": "11:00",
            "description": "Talk",
        },
        format="json",
    )

    assert response.status_code == 400
    assert ClubEvent.objects.count() == 0


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_tc020_rejects_event_with_invalid_faculty_reference(stub_iam):
    """test_id=TC-020; source_id=UC-GYM-003 Exception Flow"""
    club = _club()
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    response = client.post(
        f"{ROOT}/clubs/{club.pk}/events",
        {
            "name": "Talk", "faculty_user_id": 3999, "venue": "Auditorium",
            "date": "2026-12-01", "start_time": "10:00", "end_time": "11:00",
            "description": "Talk",
        },
        format="json",
    )

    assert response.status_code == 409
    assert ClubEvent.objects.count() == 0


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_tc021_rejects_event_with_invalid_time_range(stub_iam):
    """test_id=TC-021; source_id=UC-GYM-003 Exception Flow; Problem Statement §6 Business Constraints — Booking time"""
    club = _club()
    _person(3002, "faculty")
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    for start_time, end_time in (("10:00", "10:00"), ("11:00", "10:00")):
        response = client.post(
            f"{ROOT}/clubs/{club.pk}/events",
            {
                "name": "Talk", "faculty_user_id": 3002, "venue": "Auditorium",
                "date": "2026-12-01", "start_time": start_time, "end_time": end_time,
                "description": "Talk",
            },
            format="json",
        )
        assert response.status_code == 400
    assert ClubEvent.objects.count() == 0


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_tc022_event_storage_failure_does_not_record_booking(stub_iam, monkeypatch):
    """test_id=TC-022; source_id=UC-GYM-003 Exception Flow"""
    club = _club()
    _person(3002, "faculty")
    client = _client(stub_iam, user_id=club.coordinator_user_id)
    storage = ClubEvent._meta.get_field("poster").storage

    def fail_save(*args, **kwargs):
        raise OSError("test file storage unavailable")

    monkeypatch.setattr(storage, "save", fail_save)
    client.raise_request_exception = False

    response = client.post(
        f"{ROOT}/clubs/{club.pk}/events",
        {
            "name": "Talk",
            "faculty_user_id": 3002,
            "venue": "Auditorium",
            "date": "2026-12-01",
            "start_time": "10:00",
            "end_time": "11:00",
            "description": "Talk",
            "poster": SimpleUploadedFile("poster.txt", b"poster"),
        },
        format="multipart",
    )

    assert response.status_code >= 400
    assert not ClubEvent.objects.exists()
    assert not NotificationOutbox.objects.filter(topic="event.booked").exists()


def test_tc023_student_applies_to_confirmed_club(stub_iam):
    """test_id=TC-023; source_id=UC-GYM-004 Main Success Scenario"""
    club = _club()
    client = _client(stub_iam, user_id=4101)

    response = client.post(
        f"{ROOT}/clubs/{club.pk}/memberships",
        {"description": "I build robots"},
        format="json",
    )

    assert response.status_code == 201, response.content
    assert response.json()["status"] == MembershipApplication.Status.OPEN
    assert MembershipApplication.objects.filter(
        club=club, student_user_id=4101,
    ).exists()


def test_tc024_student_can_apply_to_another_club(stub_iam):
    """test_id=TC-024; source_id=UC-GYM-004 Alternative Flow"""
    first = _club(name="Robotics")
    second = _club(name="Debate")
    MembershipApplication.objects.create(
        club=first, student_user_id=4101, description="Existing application",
    )
    client = _client(stub_iam, user_id=4101)

    response = client.post(
        f"{ROOT}/clubs/{second.pk}/memberships",
        {"description": "I enjoy debate"},
        format="json",
    )

    assert response.status_code == 201, response.content
    assert MembershipApplication.objects.filter(
        club=first, student_user_id=4101,
    ).count() == 1
    assert MembershipApplication.objects.filter(
        club=second, student_user_id=4101,
    ).count() == 1


def test_tc025_duplicate_application_is_rejected_unchanged(stub_iam):
    """test_id=TC-025; source_id=UC-GYM-004 Exception Flow"""
    club = _club()
    existing = MembershipApplication.objects.create(
        club=club, student_user_id=4101, description="Original",
    )
    client = _client(stub_iam, user_id=4101)

    response = client.post(
        f"{ROOT}/clubs/{club.pk}/memberships",
        {"description": "Duplicate"},
        format="json",
    )

    assert response.status_code == 409
    existing.refresh_from_db()
    assert existing.description == "Original"
    assert MembershipApplication.objects.filter(club=club, student_user_id=4101).count() == 1


def test_tc026_open_club_does_not_accept_membership_application(stub_iam):
    """test_id=TC-026; source_id=Problem Statement §6 Business Constraints — Membership applications"""
    club = _club(status=Club.Status.OPEN)
    client = _client(stub_iam, user_id=4101)

    response = client.post(
        f"{ROOT}/clubs/{club.pk}/memberships",
        {"description": "I build robots"},
        format="json",
    )

    assert response.status_code == 409
    assert MembershipApplication.objects.count() == 0


def test_tc027_club_head_approves_pending_membership_with_remarks(stub_iam):
    """test_id=TC-027; source_id=UC-GYM-005 Main Success Scenario"""
    club = _club()
    application = MembershipApplication.objects.create(
        club=club, student_user_id=4101, description="I build robots",
    )
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    pending = client.get(f"{ROOT}/clubs/{club.pk}/memberships")
    response = client.post(
        f"{ROOT}/clubs/{club.pk}/memberships/{application.pk}/approve",
        {"remarks": "Welcome"},
        format="json",
    )

    assert pending.status_code == 200
    assert any(row["id"] == application.pk for row in pending.json()["results"])
    assert response.status_code == 200, response.content
    application.refresh_from_db()
    assert application.status == MembershipApplication.Status.CONFIRMED
    assert application.remarks == "Welcome"


def test_tc029_create_poll_with_minimum_choices_and_notify_audience(stub_iam):
    """test_id=TC-029; source_id=UC-GYM-006 Main Success Scenario"""
    club = _club()
    _person(4101, batch_year=2024, discipline="CSE")
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    response = client.post(
        f"{ROOT}/polls",
        {
            "club_id": club.pk,
            "title": "Choose a project",
            "description": "Vote once",
            "expires_at": (timezone.now() + timedelta(days=2)).isoformat(),
            "choices": ["Rover", "Drone"],
            "target_groups": [{"batch_year": 2024, "discipline": "CSE"}],
        },
        format="json",
    )

    assert response.status_code == 201, response.content
    poll = VotingPoll.objects.get(pk=response.json()["id"])
    assert poll.choices.count() == 2
    assert poll.target_groups.filter(batch_year=2024, discipline="CSE").exists()
    assert NotificationOutbox.objects.filter(
        topic="poll.created", recipient_user_id=4101,
    ).exists()


def test_tc030_poll_can_target_all_branches_for_configured_batch(stub_iam):
    """test_id=TC-030; source_id=UC-GYM-006 Alternative Flow"""
    club = _club()
    _person(4101, batch_year=2024, discipline="CSE")
    _person(4102, batch_year=2024, discipline="ECE")
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    response = client.post(
        f"{ROOT}/polls",
        {
            "club_id": club.pk,
            "title": "Choose a project",
            "description": "All branches",
            "expires_at": (timezone.now() + timedelta(days=2)).isoformat(),
            "choices": ["Rover", "Drone"],
            "target_groups": [{"batch_year": 2024, "discipline": "*"}],
        },
        format="json",
    )

    assert response.status_code == 201, response.content
    poll = VotingPoll.objects.get(pk=response.json()["id"])
    assert poll.target_groups.filter(batch_year=2024, discipline="*").exists()
    assert set(NotificationOutbox.objects.filter(
        topic="poll.created",
    ).values_list("recipient_user_id", flat=True)) == {4101, 4102}


def test_tc031_poll_with_fewer_than_two_choices_is_not_created(stub_iam):
    """test_id=TC-031; source_id=UC-GYM-006 Exception Flow; Problem Statement §6 Business Constraints — Poll choices"""
    club = _club()
    _person(4101, batch_year=2024, discipline="CSE")
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    response = client.post(
        f"{ROOT}/polls",
        {
            "club_id": club.pk,
            "title": "Choose a project",
            "expires_at": (timezone.now() + timedelta(days=2)).isoformat(),
            "choices": ["Rover"],
            "target_groups": [{"batch_year": 2024, "discipline": "CSE"}],
        },
        format="json",
    )

    assert response.status_code == 400
    assert VotingPoll.objects.count() == 0


def test_tc032_poll_with_invalid_target_is_not_created(stub_iam):
    """test_id=TC-032; source_id=UC-GYM-006 Exception Flow"""
    club = _club()
    _person(4101, batch_year=2024, discipline="CSE")
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    response = client.post(
        f"{ROOT}/polls",
        {
            "club_id": club.pk,
            "title": "Choose a project",
            "expires_at": (timezone.now() + timedelta(days=2)).isoformat(),
            "choices": ["Rover", "Drone"],
            "target_groups": [{"batch_year": 0, "discipline": "CSE"}],
        },
        format="json",
    )

    assert response.status_code == 400
    assert VotingPoll.objects.count() == 0


def test_tc033_eligible_student_casts_one_vote_and_tally_updates(stub_iam):
    """test_id=TC-033; source_id=UC-GYM-007 Main Success Scenario"""
    club = _club()
    _person(4101, batch_year=2024, discipline="CSE")
    poll, choice = _poll(club)
    client = _client(stub_iam, user_id=4101)

    response = client.post(
        f"{ROOT}/polls/{poll.pk}/vote",
        {"choice_id": choice.pk},
        format="json",
    )

    assert response.status_code == 200, response.content
    assert PollVote.objects.filter(
        poll=poll, choice=choice, student_user_id=4101,
    ).count() == 1
    assert choice.votes.count() == 1
    poll_list = client.get(f"{ROOT}/polls")
    assert poll_list.status_code == 200
    result = next(row for row in poll_list.json()["results"] if row["id"] == poll.pk)
    assert result["has_voted"] is True
    assert next(row for row in result["choices"] if row["id"] == choice.pk)[
        "vote_count"
    ] == 1


def test_tc034_second_vote_is_rejected_without_tally_change(stub_iam):
    """test_id=TC-034; source_id=UC-GYM-007 Exception Flow; Problem Statement §6 Business Constraints — Poll voting"""
    club = _club()
    _person(4101, batch_year=2024, discipline="CSE")
    poll, choice = _poll(club)
    PollVote.objects.create(poll=poll, choice=choice, student_user_id=4101)
    client = _client(stub_iam, user_id=4101)

    response = client.post(
        f"{ROOT}/polls/{poll.pk}/vote",
        {"choice_id": choice.pk},
        format="json",
    )

    assert response.status_code == 409
    assert PollVote.objects.filter(poll=poll).count() == 1
    assert choice.votes.count() == 1


def test_tc035_student_outside_target_audience_cannot_vote(stub_iam):
    """test_id=TC-035; source_id=UC-GYM-007 Exception Flow"""
    club = _club()
    _person(4103, batch_year=2024, discipline="ECE")
    poll, choice = _poll(club, target="CSE")
    client = _client(stub_iam, user_id=4103)

    response = client.post(
        f"{ROOT}/polls/{poll.pk}/vote",
        {"choice_id": choice.pk},
        format="json",
    )

    assert response.status_code == 409
    assert PollVote.objects.filter(poll=poll).count() == 0
    assert choice.votes.count() == 0


def test_tc036_student_cannot_vote_in_inactive_poll(stub_iam):
    """test_id=TC-036; source_id=UC-GYM-007 Exception Flow"""
    club = _club()
    _person(4101, batch_year=2024, discipline="CSE")
    poll, choice = _poll(club, expires_at=timezone.now() - timedelta(days=1))
    client = _client(stub_iam, user_id=4101)

    response = client.post(
        f"{ROOT}/polls/{poll.pk}/vote",
        {"choice_id": choice.pk},
        format="json",
    )

    assert response.status_code == 409
    assert PollVote.objects.filter(poll=poll).count() == 0
    assert choice.votes.count() == 0


def test_tc037_leadership_change_replaces_current_leaders(stub_iam):
    """test_id=TC-037; source_id=UC-GYM-008 Main Success Scenario"""
    club = _club()
    _person(2003)
    _person(2004)
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    response = client.post(
        f"{ROOT}/clubs/{club.pk}/leadership",
        {"coordinator_user_id": 2003, "co_coordinator_user_id": 2004},
        format="json",
    )

    assert response.status_code == 200, response.content
    club.refresh_from_db()
    assert club.coordinator_user_id == 2003
    assert club.co_coordinator_user_id == 2004


def test_tc038_invalid_coordinator_preserves_current_leadership(stub_iam):
    """test_id=TC-038; source_id=UC-GYM-008 Exception Flow; Problem Statement §6 Business Constraints — Student leaders"""
    club = _club()
    _person(2002)
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    response = client.post(
        f"{ROOT}/clubs/{club.pk}/leadership",
        {"coordinator_user_id": 2999, "co_coordinator_user_id": 2002},
        format="json",
    )

    assert response.status_code == 409
    club.refresh_from_db()
    assert (club.coordinator_user_id, club.co_coordinator_user_id) == (2001, 2002)


def test_tc039_invalid_co_coordinator_preserves_current_leadership(stub_iam):
    """test_id=TC-039; source_id=UC-GYM-008 Exception Flow; Problem Statement §6 Business Constraints — Student leaders"""
    club = _club()
    _person(2001)
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    response = client.post(
        f"{ROOT}/clubs/{club.pk}/leadership",
        {"coordinator_user_id": 2001, "co_coordinator_user_id": 2999},
        format="json",
    )

    assert response.status_code == 409
    club.refresh_from_db()
    assert (club.coordinator_user_id, club.co_coordinator_user_id) == (2001, 2002)


def test_tc040_unauthorized_actor_cannot_change_leadership(stub_iam):
    """test_id=TC-040; source_id=UC-GYM-008 Exception Flow"""
    club = _club()
    client = _client(stub_iam, user_id=2003)

    response = client.post(
        f"{ROOT}/clubs/{club.pk}/leadership",
        {"coordinator_user_id": 2003, "co_coordinator_user_id": 2004},
        format="json",
    )

    assert response.status_code == 403
    club.refresh_from_db()
    assert (club.coordinator_user_id, club.co_coordinator_user_id) == (2001, 2002)


def test_tc041_budget_request_accepts_zero_amount(stub_iam):
    """test_id=TC-041; source_id=UC-GYM-009 Main Success Scenario; Problem Statement §6 Business Constraints — Budget amount"""
    club = _club()
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    response = client.post(
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
    budget = BudgetRequest.objects.get(club=club)
    assert budget.amount == 0
    assert budget.status == "open"
    assert budget.supporting_file.storage.exists(budget.supporting_file.name)


def test_tc042_negative_budget_amount_is_rejected(stub_iam):
    """test_id=TC-042; source_id=UC-GYM-009 Exception Flow; Problem Statement §6 Business Constraints — Budget amount"""
    club = _club()
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    response = client.post(
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
    assert club.budget_requests.count() == 0


def test_tc043_budget_request_without_supporting_file_is_rejected(stub_iam):
    """test_id=TC-043; source_id=UC-GYM-009 Exception Flow; Problem Statement §6 Business Constraints — Budget supporting file"""
    club = _club()
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    response = client.post(
        f"{ROOT}/clubs/{club.pk}/budgets",
        {"amount": "0", "purpose": "Parts", "description": "No file"},
        format="multipart",
    )

    assert response.status_code == 400
    assert club.budget_requests.count() == 0


def test_tc044_club_head_submits_documented_event_report(stub_iam):
    """test_id=TC-044; source_id=UC-GYM-010 Main Success Scenario"""
    club = _club()
    _person(4001)
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    response = client.post(
        f"{ROOT}/clubs/{club.pk}/reports",
        _valid_report_payload(),
        format="multipart",
    )

    assert response.status_code == 201, response.content
    report = ClubEventReport.objects.get(pk=response.json()["id"], club=club)
    assert report.report_file.storage.exists(report.report_file.name)


def test_tc045_event_report_without_required_file_is_rejected(stub_iam):
    """test_id=TC-045; source_id=UC-GYM-010 Exception Flow; Problem Statement §6 Business Constraints — Event report file"""
    club = _club()
    _person(4001)
    payload = _valid_report_payload()
    payload.pop("report_file")
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    response = client.post(
        f"{ROOT}/clubs/{club.pk}/reports",
        payload,
        format="multipart",
    )

    assert response.status_code == 400
    assert club.reports.count() == 0


def test_tc046_event_report_with_invalid_student_reference_is_rejected(stub_iam):
    """test_id=TC-046; source_id=UC-GYM-010 Exception Flow"""
    club = _club()
    payload = _valid_report_payload()
    payload["student_incharge_user_id"] = 4999
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    response = client.post(
        f"{ROOT}/clubs/{club.pk}/reports",
        payload,
        format="multipart",
    )

    assert response.status_code == 409
    assert club.reports.count() == 0


def test_tc047_event_report_with_missing_student_reference_is_rejected(stub_iam):
    """test_id=TC-047; source_id=UC-GYM-010 Exception Flow"""
    club = _club()
    payload = _valid_report_payload()
    payload.pop("student_incharge_user_id")
    client = _client(stub_iam, user_id=club.coordinator_user_id)

    response = client.post(
        f"{ROOT}/clubs/{club.pk}/reports",
        payload,
        format="multipart",
    )

    assert response.status_code == 400
    assert club.reports.count() == 0


def test_tc048_assigned_faculty_can_access_and_review_report(stub_iam):
    """test_id=TC-048; source_id=UC-GYM-012 Main Success Scenario"""
    club = _club()
    _person(4001)
    head = _client(stub_iam, user_id=club.coordinator_user_id)
    submitted = head.post(
        f"{ROOT}/clubs/{club.pk}/reports",
        _valid_report_payload(),
        format="multipart",
    )
    assert submitted.status_code == 201, submitted.content

    assigned = _client(
        stub_iam,
        user_id=club.faculty_councillor_user_id,
        kind="faculty",
        role="faculty",
        permissions=FACULTY,
    )
    listed = assigned.get(f"{ROOT}/reports/assigned")
    assert listed.status_code == 200
    assert listed.json()["results"][0]["event_name"] == "Robot showcase"
    downloaded = assigned.get(submitted.json()["download_url"])
    assert downloaded.status_code == 200
    assert b"event report" in b"".join(downloaded.streaming_content)


def test_tc049_unassigned_faculty_cannot_access_club_report(stub_iam):
    """test_id=TC-049; source_id=UC-GYM-012 Exception Flow; Problem Statement §8 Success Criteria — Assigned councillor access"""
    club = _club()
    _person(3002, "faculty")
    _person(4001)
    head = _client(stub_iam, user_id=club.coordinator_user_id)
    submitted = head.post(
        f"{ROOT}/clubs/{club.pk}/reports",
        _valid_report_payload(),
        format="multipart",
    )
    assert submitted.status_code == 201, submitted.content
    unrelated = _client(
        stub_iam, user_id=3002, kind="faculty", role="faculty", permissions=FACULTY,
    )

    response = unrelated.get(submitted.json()["download_url"])

    assert response.status_code == 403
    assert b"event report" not in response.content
