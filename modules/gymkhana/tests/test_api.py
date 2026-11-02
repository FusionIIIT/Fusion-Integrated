import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.gymkhana import registry
from modules.gymkhana.models import (
    Club,
    ClubEvent,
    ClubSession,
    MembershipApplication,
    NotificationOutbox,
    PollVote,
    VotingPoll,
)

pytestmark = pytest.mark.django_db

ROOT = "/api/v1/gymkhana"
ALL_STUDENT = tuple(registry.ROLE_GRANTS["student"])
ADMIN = tuple(registry.ROLE_GRANTS["Student Admin"])
FACULTY = tuple(registry.ROLE_GRANTS["faculty"])


def _client(stub_iam, *, user_id=2001, kind="student", role=None, permissions=None,
            modules=("gymkhana",)):
    role = role or kind
    grants = permissions if permissions is not None else registry.ROLE_GRANTS[role]
    stub_iam(make_session(
        user_id=user_id,
        kind=kind,
        roles=(role,),
        active_role=role,
        modules=modules,
        permissions=grants,
    ))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


def _person(user_id, kind, *, batch_year=2024, discipline="CSE"):
    return UserRef.objects.create(
        user_id=user_id,
        username=f"u{user_id}",
        display_name=f"Person {user_id}",
        kind=kind,
        batch_year=batch_year if kind == "student" else None,
        discipline=discipline if kind == "student" else "",
    )


def _club(*, status=Club.Status.CONFIRMED):
    return Club.objects.create(
        name="Robotics",
        category=Club.Category.TECHNICAL,
        coordinator_user_id=2001,
        co_coordinator_user_id=2002,
        faculty_councillor_user_id=3001,
        description="Build things",
        status=status,
    )


def test_student_admin_creates_and_confirms_club(stub_iam):
    _person(2001, "student")
    _person(2002, "student")
    _person(3001, "faculty")
    client = _client(stub_iam, user_id=9001, role="Student Admin",
                     permissions=ADMIN)
    data = {
        "name": "Robotics",
        "category": "Technical",
        "coordinator_user_id": 2001,
        "co_coordinator_user_id": 2002,
        "faculty_councillor_user_id": 3001,
        "description": "Build things",
    }

    created = client.post(f"{ROOT}/clubs", data, format="json")

    assert created.status_code == 201, created.content
    assert created.json()["status"] == "open"
    approved = client.post(f"{ROOT}/clubs/{created.json()['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "confirmed"


def test_invalid_club_person_and_non_admin_are_rejected(stub_iam):
    client = _client(stub_iam, user_id=2001)
    data = {
        "name": "Robotics",
        "category": "Technical",
        "coordinator_user_id": 2001,
        "co_coordinator_user_id": 2002,
        "faculty_councillor_user_id": 3001,
        "description": "Build things",
    }
    assert client.post(f"{ROOT}/clubs", data, format="json").status_code == 403
    client = _client(stub_iam, user_id=9001, role="Student Admin",
                     permissions=ADMIN)
    response = client.post(f"{ROOT}/clubs", data, format="json")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_student_assignment"


def test_membership_requires_confirmed_club_and_only_head_can_approve(stub_iam):
    club = _club(status=Club.Status.OPEN)
    student = _client(stub_iam, user_id=4001)
    body = {"description": "I build robots"}
    assert student.post(f"{ROOT}/clubs/{club.pk}/memberships", body,
                        format="json").status_code == 409

    club.status = Club.Status.CONFIRMED
    club.save(update_fields=["status"])
    submitted = student.post(f"{ROOT}/clubs/{club.pk}/memberships", body,
                             format="json")
    assert submitted.status_code == 201
    application_id = submitted.json()["id"]
    duplicate = student.post(f"{ROOT}/clubs/{club.pk}/memberships", body,
                             format="json")
    assert duplicate.status_code == 409

    other_student = _client(stub_iam, user_id=4002)
    denied = other_student.post(
        f"{ROOT}/clubs/{club.pk}/memberships/{application_id}/approve",
        {"remarks": "welcome"}, format="json",
    )
    assert denied.status_code == 403
    head = _client(stub_iam, user_id=club.coordinator_user_id)
    approved = head.post(
        f"{ROOT}/clubs/{club.pk}/memberships/{application_id}/approve",
        {"remarks": "welcome"}, format="json",
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "confirmed"
    assert MembershipApplication.objects.get(pk=application_id).remarks == "welcome"


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_session_and_event_conflicts_are_checked_across_types(stub_iam):
    club = _club()
    _person(3002, "faculty")
    ClubSession.objects.create(
        club=club, venue="Auditorium", date="2026-12-01",
        start_time="10:00", end_time="11:00",
        description="Session", created_by_user_id=2001,
    )
    client = _client(stub_iam, user_id=club.coordinator_user_id)
    event = client.post(
        f"{ROOT}/clubs/{club.pk}/events",
        {
            "name": "Talk", "faculty_user_id": 3002, "venue": "Auditorium",
            "date": "2026-12-01", "start_time": "10:30",
            "end_time": "11:30", "description": "Guest talk",
        },
        format="json",
    )
    assert event.status_code == 409
    assert event.json()["error"]["code"] == "venue_conflict"

    adjacent = client.post(
        f"{ROOT}/clubs/{club.pk}/events",
        {
            "name": "Talk", "faculty_user_id": 3002, "venue": "Auditorium",
            "date": "2026-12-01", "start_time": "11:00",
            "end_time": "12:00", "description": "Guest talk",
        },
        format="json",
    )
    assert adjacent.status_code == 201, adjacent.content
    assert ClubEvent.objects.count() == 1
    assert NotificationOutbox.objects.count() == 0


def test_poll_targeting_expiry_and_one_vote(stub_iam):
    club = _club()
    _person(4101, "student", batch_year=2024, discipline="CSE")
    _person(4102, "student", batch_year=2024, discipline="CSE")
    _person(4103, "student", batch_year=2024, discipline="ECE")
    head = _client(stub_iam, user_id=club.coordinator_user_id)
    created = head.post(
        f"{ROOT}/polls",
        {
            "club_id": club.pk,
            "title": "Choose a project",
            "description": "Vote once",
            "expires_at": "2027-01-01T10:00:00+05:30",
            "choices": ["Rover", "Drone"],
            "target_groups": [{"batch_year": 2024, "discipline": "CSE"}],
        },
        format="json",
    )
    assert created.status_code == 201, created.content
    poll = VotingPoll.objects.get()
    assert NotificationOutbox.objects.count() == 2
    choice_id = created.json()["choices"][0]["id"]

    voter = _client(stub_iam, user_id=4101)
    accepted = voter.post(
        f"{ROOT}/polls/{poll.pk}/vote", {"choice_id": choice_id}, format="json",
    )
    assert accepted.status_code == 200
    repeated = voter.post(
        f"{ROOT}/polls/{poll.pk}/vote", {"choice_id": choice_id}, format="json",
    )
    assert repeated.status_code == 409
    assert PollVote.objects.count() == 1

    outsider = _client(stub_iam, user_id=4103)
    refused = outsider.post(
        f"{ROOT}/polls/{poll.pk}/vote", {"choice_id": choice_id}, format="json",
    )
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "poll_not_targeted"


def test_budget_and_report_files_require_files_and_scope_download(stub_iam):
    club = _club()
    _person(4001, "student")
    _person(3002, "faculty")
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    missing_file = head.post(
        f"{ROOT}/clubs/{club.pk}/budgets",
        {"amount": "0", "purpose": "Parts", "description": "No file"},
        format="multipart",
    )
    assert missing_file.status_code == 400

    budget = head.post(
        f"{ROOT}/clubs/{club.pk}/budgets",
        {
            "amount": "0",
            "purpose": "Parts",
            "description": "Prototype materials",
            "supporting_file": SimpleUploadedFile("quote.txt", b"vendor quote"),
        },
        format="multipart",
    )
    assert budget.status_code == 201, budget.content
    assert budget.json()["status"] == "open"
    assert "supporting_file" not in budget.json()

    report = head.post(
        f"{ROOT}/clubs/{club.pk}/reports",
        {
            "student_incharge_user_id": 4001,
            "event_name": "Robot showcase",
            "event_at": "2026-11-01T12:00:00+05:30",
            "description": "Summary",
            "report_file": SimpleUploadedFile("report.txt", b"event report"),
        },
        format="multipart",
    )
    assert report.status_code == 201, report.content
    assert "report_file" not in report.json()
    assert head.get(report.json()["download_url"]).status_code == 200

    assigned = _client(stub_iam, user_id=club.faculty_councillor_user_id,
                       kind="faculty", role="faculty", permissions=FACULTY)
    assert assigned.get(f"{ROOT}/reports/assigned").json()["results"][0]["event_name"] == (
        "Robot showcase"
    )
    assert assigned.get(report.json()["download_url"]).status_code == 200
    unrelated = _client(stub_iam, user_id=3002, kind="faculty", role="faculty",
                        permissions=FACULTY)
    assert unrelated.get(report.json()["download_url"]).status_code == 403


def test_unassigned_faculty_cannot_list_club_reports(stub_iam):
    club = _club()
    _person(3002, "faculty")
    unrelated = _client(stub_iam, user_id=3002, kind="faculty",
                        role="faculty", permissions=FACULTY)
    response = unrelated.get(f"{ROOT}/clubs/{club.pk}/reports")
    assert response.status_code == 403
