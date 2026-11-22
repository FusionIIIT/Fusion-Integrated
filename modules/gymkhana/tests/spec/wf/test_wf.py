from datetime import timedelta
from unittest.mock import patch

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
        email=f"user{user_id}@example.test",
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


def _poll_payload(club_id, **overrides):
    return {
        "club_id": club_id,
        "title": "Choose a project",
        "description": "Vote once",
        "expires_at": (timezone.now() + timedelta(days=30)).isoformat(),
        "choices": ["Rover", "Drone"],
        "target_groups": [{"batch_year": 2024, "discipline": "CSE"}],
        **overrides,
    }


def _create_poll(client, club, **overrides):
    response = client.post(
        f"{ROOT}/polls", _poll_payload(club.pk, **overrides), format="json",
    )
    assert response.status_code == 201, response.content
    return response, VotingPoll.objects.get(pk=response.json()["id"])


def _deliver_notifications():
    from modules.gymkhana.services.notifications import deliver_pending

    with patch("modules.gymkhana.services.notifications.send_mail") as send_mail:
        result = deliver_pending()
    return result, send_mail


def test_tc001_student_admin_creates_open_club(stub_iam):
    """test_id=TC-001; source_id=UC-GYM-001 Main Flow (BW-GYM-03, Club Not Created → Club Open)"""
    _person(2001)
    _person(2002)
    _person(3001, "faculty")
    admin = _client(stub_iam, user_id=9001, role="Student Admin", permissions=ADMIN)

    response = admin.post(f"{ROOT}/clubs", _club_payload(), format="json")

    assert response.status_code == 201, response.content
    assert response.json()["status"] == Club.Status.OPEN
    assert Club.objects.filter(pk=response.json()["id"], status=Club.Status.OPEN).exists()


def test_tc002_required_club_data_is_enforced(stub_iam):
    """test_id=TC-002; source_id=UC-GYM-001 Main Flow; Problem Statement §6 Business Constraints — required club data"""
    _person(2001)
    _person(2002)
    _person(3001, "faculty")
    admin = _client(stub_iam, user_id=9001, role="Student Admin", permissions=ADMIN)
    payload = _club_payload()
    payload.pop("description")

    response = admin.post(f"{ROOT}/clubs", payload, format="json")

    assert response.status_code == 400
    assert not Club.objects.exists()


def test_tc003_invalid_coordinator_prevents_club_creation(stub_iam):
    """test_id=TC-003; source_id=Problem Statement §6 Business Constraints — coordinator assignments must refer to valid students"""
    _person(2002)
    _person(3001, "faculty")
    admin = _client(stub_iam, user_id=9001, role="Student Admin", permissions=ADMIN)

    response = admin.post(
        f"{ROOT}/clubs", _club_payload(coordinator_user_id=9991), format="json",
    )

    assert response.status_code == 409
    assert not Club.objects.exists()


def test_tc004_invalid_co_coordinator_prevents_club_creation(stub_iam):
    """test_id=TC-004; source_id=Problem Statement §6 Business Constraints — co-coordinator assignments must refer to valid students"""
    _person(2001)
    _person(3001, "faculty")
    admin = _client(stub_iam, user_id=9001, role="Student Admin", permissions=ADMIN)

    response = admin.post(
        f"{ROOT}/clubs", _club_payload(co_coordinator_user_id=9992), format="json",
    )

    assert response.status_code == 409
    assert not Club.objects.exists()


def test_tc005_invalid_faculty_prevents_club_creation(stub_iam):
    """test_id=TC-005; source_id=Problem Statement §6 Business Constraints — Club Faculty Councillor must be a valid faculty member"""
    _person(2001)
    _person(2002)
    admin = _client(stub_iam, user_id=9001, role="Student Admin", permissions=ADMIN)

    response = admin.post(
        f"{ROOT}/clubs", _club_payload(faculty_councillor_user_id=9993), format="json",
    )

    assert response.status_code == 409
    assert not Club.objects.exists()


def test_tc006_rejects_category_outside_allowed_set(stub_iam):
    """test_id=TC-006; source_id=Problem Statement §6 Business Constraints — club category is restricted to Technical, Sports, or Cultural"""
    _person(2001)
    _person(2002)
    _person(3001, "faculty")
    admin = _client(stub_iam, user_id=9001, role="Student Admin", permissions=ADMIN)

    response = admin.post(
        f"{ROOT}/clubs", _club_payload(category="Other"), format="json",
    )

    assert response.status_code == 400
    assert not Club.objects.exists()


def test_tc007_student_admin_approval_confirms_open_club(stub_iam):
    """test_id=TC-007; source_id=UC-GYM-011 Main Flow (BW-GYM-03, Club Open → Club Confirmed)"""
    club = _club(status=Club.Status.OPEN)
    admin = _client(stub_iam, user_id=9001, role="Student Admin", permissions=ADMIN)

    response = admin.post(f"{ROOT}/clubs/{club.pk}/approve")

    assert response.status_code == 200
    club.refresh_from_db()
    assert club.status == Club.Status.CONFIRMED


def test_tc008_non_admin_cannot_confirm_open_club(stub_iam):
    """test_id=TC-008; source_id=Problem Statement §3.1 Club Governance; §4.1 In Scope — club activation under Student Admin control"""
    club = _club(status=Club.Status.OPEN)
    student = _client(stub_iam, user_id=2001)

    response = student.post(f"{ROOT}/clubs/{club.pk}/approve")

    assert response.status_code == 403
    club.refresh_from_db()
    assert club.status == Club.Status.OPEN


def test_tc009_leadership_change_updates_current_assignments(stub_iam):
    """test_id=TC-009; source_id=Problem Statement §2 Problem Domain; §4.1 In Scope — club leadership changes and current leadership assignment"""
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
    assert (club.coordinator_user_id, club.co_coordinator_user_id) == (2101, 2102)


def test_tc010_invalid_leadership_assignment_preserves_current_leaders(stub_iam):
    """test_id=TC-010; source_id=Problem Statement §6 Business Constraints — coordinator and co-coordinator assignments must refer to valid students"""
    club = _club()
    _person(2102)
    head = _client(stub_iam, user_id=club.coordinator_user_id)
    old_leadership = (club.coordinator_user_id, club.co_coordinator_user_id)

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/leadership",
        {"coordinator_user_id": 9991, "co_coordinator_user_id": 2102},
        format="json",
    )

    assert response.status_code == 409
    club.refresh_from_db()
    assert (club.coordinator_user_id, club.co_coordinator_user_id) == old_leadership


def test_tc011_student_applies_to_confirmed_club(stub_iam):
    """test_id=TC-011; source_id=UC-GYM-004 Main Flow (BW-GYM-01, No Membership Application → Membership Application Open)"""
    club = _club()
    student = _client(stub_iam, user_id=4101)

    response = student.post(
        f"{ROOT}/clubs/{club.pk}/memberships",
        {"description": "I build robots"},
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["status"] == MembershipApplication.Status.OPEN
    assert MembershipApplication.objects.filter(
        pk=response.json()["id"], club=club, student_user_id=4101,
    ).exists()


def test_tc012_open_club_rejects_membership_application(stub_iam):
    """test_id=TC-012; source_id=Problem Statement §6 Business Constraints — membership applications are allowed only for confirmed clubs"""
    club = _club(status=Club.Status.OPEN)
    student = _client(stub_iam, user_id=4101)

    response = student.post(
        f"{ROOT}/clubs/{club.pk}/memberships",
        {"description": "I build robots"},
        format="json",
    )

    assert response.status_code == 409
    assert not MembershipApplication.objects.exists()


def test_tc013_duplicate_application_is_not_created(stub_iam):
    """test_id=TC-013; source_id=Problem Statement §6 Business Constraints — duplicate applications to the same club must be prevented"""
    club = _club()
    existing = MembershipApplication.objects.create(
        club=club, student_user_id=4101, description="Existing application",
    )
    student = _client(stub_iam, user_id=4101)

    response = student.post(
        f"{ROOT}/clubs/{club.pk}/memberships",
        {"description": "Duplicate application"},
        format="json",
    )

    assert response.status_code == 409
    assert MembershipApplication.objects.count() == 1
    existing.refresh_from_db()
    assert existing.status == MembershipApplication.Status.OPEN


def test_tc014_student_can_apply_to_two_different_clubs(stub_iam):
    """test_id=TC-014; source_id=Problem Statement §3.3 Membership Management; §6 Business Constraints — applications to different clubs remain allowed"""
    first = _club(name="Robotics")
    second = _club(name="Astronomy")
    student = _client(stub_iam, user_id=4101)

    first_response = student.post(
        f"{ROOT}/clubs/{first.pk}/memberships",
        {"description": "Robotics application"},
        format="json",
    )
    second_response = student.post(
        f"{ROOT}/clubs/{second.pk}/memberships",
        {"description": "Astronomy application"},
        format="json",
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert MembershipApplication.objects.filter(
        student_user_id=4101, status=MembershipApplication.Status.OPEN,
    ).count() == 2


def test_tc015_applicable_club_head_approves_open_membership(stub_iam):
    """test_id=TC-015; source_id=UC-GYM-005 Main Flow (BW-GYM-01, Membership Application Open → Membership Confirmed)"""
    club = _club()
    application = MembershipApplication.objects.create(
        club=club, student_user_id=4101, description="I build robots",
    )
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/memberships/{application.pk}/approve",
        {},
        format="json",
    )

    assert response.status_code == 200
    application.refresh_from_db()
    assert application.status == MembershipApplication.Status.CONFIRMED


def test_tc016_other_club_head_cannot_approve_membership(stub_iam):
    """test_id=TC-016; source_id=Problem Statement §6 Business Constraints — only the applicable Club Head may approve pending membership applications"""
    club = _club()
    other_club = _club(name="Chess")
    other_club.coordinator_user_id = 2201
    other_club.save(update_fields=["coordinator_user_id"])
    application = MembershipApplication.objects.create(
        club=club, student_user_id=4101, description="I build robots",
    )
    other_club_head = _client(stub_iam, user_id=2201)

    response = other_club_head.post(
        f"{ROOT}/clubs/{club.pk}/memberships/{application.pk}/approve",
        {},
        format="json",
    )

    assert response.status_code == 403
    application.refresh_from_db()
    assert application.status == MembershipApplication.Status.OPEN


def test_tc017_create_poll_and_deliver_to_target_audience(stub_iam):
    """test_id=TC-017; source_id=UC-GYM-006 Main Flow (BW-GYM-02, Poll Not Available → Poll Open / Target Audience Defined); Problem Statement §3.6 Student Polling"""
    club = _club()
    _person(4101, batch_year=2024, discipline="CSE")
    _person(4102, batch_year=2024, discipline="CSE")
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response, poll = _create_poll(head, club)

    assert poll.is_active
    assert poll.choices.count() == 2
    assert poll.target_groups.filter(batch_year=2024, discipline="CSE").exists()
    delivery, send_mail = _deliver_notifications()
    assert delivery == {"sent": 2, "failed": 0, "deferred": 0}
    assert send_mail.call_count == 2
    assert NotificationOutbox.objects.filter(
        topic="poll.created", status=NotificationOutbox.Status.SENT,
    ).count() == 2
    assert response.json()["id"] == poll.pk


def test_tc018_non_applicable_club_head_cannot_create_poll(stub_iam):
    """test_id=TC-018; source_id=UC-GYM-006 Main Flow (BW-GYM-02, actor is applicable Club Head)"""
    club = _club()
    other_club = _club(name="Chess")
    other_club.coordinator_user_id = 2201
    other_club.save(update_fields=["coordinator_user_id"])
    _person(4101, batch_year=2024, discipline="CSE")
    other_head = _client(stub_iam, user_id=2201)

    response = other_head.post(
        f"{ROOT}/polls", _poll_payload(club.pk), format="json",
    )

    assert response.status_code == 403
    assert not VotingPoll.objects.exists()


def test_tc019_poll_requires_at_least_two_choices(stub_iam):
    """test_id=TC-019; source_id=Problem Statement §6 Business Constraints — a voting poll must contain at least two choices"""
    club = _club()
    _person(4101, batch_year=2024, discipline="CSE")
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/polls",
        _poll_payload(club.pk, choices=["Only one"]),
        format="json",
    )

    assert response.status_code == 400
    assert not VotingPoll.objects.exists()


def test_tc020_poll_rejects_invalid_target_groups(stub_iam):
    """test_id=TC-020; source_id=UC-GYM-006 Main Flow (BW-GYM-02, valid target groups)"""
    club = _club()
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/polls",
        _poll_payload(
            club.pk, target_groups=[{"batch_year": 0, "discipline": "CSE"}],
        ),
        format="json",
    )

    assert response.status_code == 400
    assert not VotingPoll.objects.exists()


def test_tc021_eligible_student_records_vote_in_active_poll(stub_iam):
    """test_id=TC-021; source_id=UC-GYM-007 Main Flow (BW-GYM-02, Poll Open / Target Audience Defined / Student Not Yet Voted → Student Vote Recorded)"""
    club = _club()
    _person(4101, batch_year=2024, discipline="CSE")
    head = _client(stub_iam, user_id=club.coordinator_user_id)
    created, poll = _create_poll(head, club)
    choice_id = created.json()["choices"][0]["id"]
    student = _client(stub_iam, user_id=4101)

    response = student.post(
        f"{ROOT}/polls/{poll.pk}/vote", {"choice_id": choice_id}, format="json",
    )

    assert response.status_code == 200
    assert PollVote.objects.filter(
        poll=poll, student_user_id=4101, choice_id=choice_id,
    ).exists()
    poll.refresh_from_db()
    assert poll.is_active
    assert poll.target_groups.filter(batch_year=2024, discipline="CSE").exists()


def test_tc022_inactive_poll_rejects_vote(stub_iam):
    """test_id=TC-022; source_id=UC-GYM-007 Main Flow (BW-GYM-02, poll active guard)"""
    club = _club()
    _person(4101, batch_year=2024, discipline="CSE")
    poll = VotingPoll.objects.create(
        club=club,
        title="Choose a project",
        expires_at=timezone.now() + timedelta(days=2),
        created_by_user_id=club.coordinator_user_id,
        is_active=False,
    )
    choice = PollChoice.objects.create(poll=poll, text="Rover")
    student = _client(stub_iam, user_id=4101)

    response = student.post(
        f"{ROOT}/polls/{poll.pk}/vote", {"choice_id": choice.pk}, format="json",
    )

    assert response.status_code == 409
    assert not PollVote.objects.filter(poll=poll).exists()


def test_tc023_expired_poll_rejects_vote(stub_iam):
    """test_id=TC-023; source_id=UC-GYM-007 Main Flow (BW-GYM-02, poll unexpired guard)"""
    club = _club()
    _person(4101, batch_year=2024, discipline="CSE")
    poll = VotingPoll.objects.create(
        club=club,
        title="Choose a project",
        expires_at=timezone.now() - timedelta(seconds=1),
        created_by_user_id=club.coordinator_user_id,
    )
    choice = PollChoice.objects.create(poll=poll, text="Rover")
    student = _client(stub_iam, user_id=4101)

    response = student.post(
        f"{ROOT}/polls/{poll.pk}/vote", {"choice_id": choice.pk}, format="json",
    )

    assert response.status_code == 409
    assert not PollVote.objects.filter(poll=poll).exists()


def test_tc024_student_outside_target_audience_cannot_vote(stub_iam):
    """test_id=TC-024; source_id=UC-GYM-007 Main Flow (BW-GYM-02, student belongs to target audience guard)"""
    club = _club()
    _person(4101, batch_year=2024, discipline="ECE")
    poll = VotingPoll.objects.create(
        club=club,
        title="Choose a project",
        expires_at=timezone.now() + timedelta(days=2),
        created_by_user_id=club.coordinator_user_id,
    )
    choice = PollChoice.objects.create(poll=poll, text="Rover")
    poll.target_groups.create(batch_year=2024, discipline="CSE")
    student = _client(stub_iam, user_id=4101)

    response = student.post(
        f"{ROOT}/polls/{poll.pk}/vote", {"choice_id": choice.pk}, format="json",
    )

    assert response.status_code == 409
    assert not PollVote.objects.filter(poll=poll).exists()


def test_tc025_student_cannot_vote_twice_in_poll(stub_iam):
    """test_id=TC-025; source_id=Problem Statement §3.6 Student Polling; §6 Business Constraints — at most one vote per student per poll"""
    club = _club()
    _person(4101, batch_year=2024, discipline="CSE")
    poll = VotingPoll.objects.create(
        club=club,
        title="Choose a project",
        expires_at=timezone.now() + timedelta(days=2),
        created_by_user_id=club.coordinator_user_id,
    )
    choice = PollChoice.objects.create(poll=poll, text="Rover")
    poll.target_groups.create(batch_year=2024, discipline="CSE")
    PollVote.objects.create(poll=poll, choice=choice, student_user_id=4101)
    student = _client(stub_iam, user_id=4101)

    response = student.post(
        f"{ROOT}/polls/{poll.pk}/vote", {"choice_id": choice.pk}, format="json",
    )

    assert response.status_code == 409
    assert PollVote.objects.filter(poll=poll, student_user_id=4101).count() == 1


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_tc026_book_session_and_deliver_notification(stub_iam):
    """test_id=TC-026; source_id=Problem Statement §4.1 In Scope — session booking and notifications for newly booked sessions"""
    club = _club()
    member = _person(4101)
    MembershipApplication.objects.create(
        club=club,
        student_user_id=member.user_id,
        description="Member",
        status=MembershipApplication.Status.CONFIRMED,
    )
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/sessions",
        {
            "venue": "Auditorium",
            "date": "2026-12-01",
            "start_time": "10:00",
            "end_time": "11:00",
            "description": "Club session",
        },
        format="json",
    )

    assert response.status_code == 201
    assert ClubSession.objects.filter(pk=response.json()["id"]).exists()
    delivery, send_mail = _deliver_notifications()
    assert delivery == {"sent": 1, "failed": 0, "deferred": 0}
    assert send_mail.call_count == 1
    assert NotificationOutbox.objects.get(
        topic="session.booked", recipient_user_id=member.user_id,
    ).status == NotificationOutbox.Status.SENT


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_tc027_book_event_and_deliver_notification(stub_iam):
    """test_id=TC-027; source_id=Problem Statement §4.1 In Scope — event booking and notifications for newly booked events"""
    club = _club()
    member = _person(4101)
    _person(3002, "faculty")
    MembershipApplication.objects.create(
        club=club,
        student_user_id=member.user_id,
        description="Member",
        status=MembershipApplication.Status.CONFIRMED,
    )
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/events",
        {
            "name": "Club event",
            "faculty_user_id": 3002,
            "venue": "Auditorium",
            "date": "2026-12-02",
            "start_time": "10:00",
            "end_time": "11:00",
            "description": "Club event",
        },
        format="json",
    )

    assert response.status_code == 201
    assert ClubEvent.objects.filter(pk=response.json()["id"]).exists()
    delivery, send_mail = _deliver_notifications()
    assert delivery == {"sent": 1, "failed": 0, "deferred": 0}
    assert send_mail.call_count == 1
    assert NotificationOutbox.objects.get(
        topic="event.booked", recipient_user_id=member.user_id,
    ).status == NotificationOutbox.Status.SENT


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_tc028_booking_with_equal_start_and_end_is_rejected(stub_iam):
    """test_id=TC-028; source_id=Problem Statement §6 Business Constraints — a booking start time must precede its end time"""
    club = _club()
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/sessions",
        {
            "venue": "Auditorium",
            "date": "2026-12-03",
            "start_time": "10:00",
            "end_time": "10:00",
            "description": "Invalid session",
        },
        format="json",
    )

    assert response.status_code == 400
    assert not ClubSession.objects.exists()


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_tc029_session_cannot_overlap_session_at_same_venue_and_date(stub_iam):
    """test_id=TC-029; source_id=Problem Statement §6 Business Constraints; §8 Success Criteria — prevent session-session overlap in the same venue on the same date"""
    club = _club()
    existing = ClubSession.objects.create(
        club=club,
        venue="Auditorium",
        date="2026-12-03",
        start_time="10:00",
        end_time="11:00",
        description="Existing session",
        created_by_user_id=club.coordinator_user_id,
    )
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/sessions",
        {
            "venue": "Auditorium",
            "date": "2026-12-03",
            "start_time": "10:30",
            "end_time": "11:30",
            "description": "Overlapping session",
        },
        format="json",
    )

    assert response.status_code == 409
    assert ClubSession.objects.count() == 1
    assert ClubSession.objects.get(pk=existing.pk).description == "Existing session"


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_tc030_event_cannot_overlap_event_at_same_venue_and_date(stub_iam):
    """test_id=TC-030; source_id=Problem Statement §6 Business Constraints; §8 Success Criteria — prevent event-event overlap in the same venue on the same date"""
    club = _club()
    _person(3002, "faculty")
    existing = ClubEvent.objects.create(
        club=club,
        name="Existing event",
        venue="Auditorium",
        date="2026-12-03",
        start_time="10:00",
        end_time="11:00",
        description="Existing event",
        faculty_user_id=3002,
        created_by_user_id=club.coordinator_user_id,
    )
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/events",
        {
            "name": "Overlapping event",
            "faculty_user_id": 3002,
            "venue": "Auditorium",
            "date": "2026-12-03",
            "start_time": "10:30",
            "end_time": "11:30",
            "description": "Overlap",
        },
        format="json",
    )

    assert response.status_code == 409
    assert ClubEvent.objects.count() == 1
    assert ClubEvent.objects.get(pk=existing.pk).name == "Existing event"


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_tc031_session_cannot_overlap_event_at_same_venue_and_date(stub_iam):
    """test_id=TC-031; source_id=Problem Statement §3.2 Venue Scheduling; §8 Success Criteria — prevent session-event overlap in the same venue on the same date"""
    club = _club()
    _person(3002, "faculty")
    existing = ClubEvent.objects.create(
        club=club,
        name="Existing event",
        venue="Auditorium",
        date="2026-12-03",
        start_time="10:00",
        end_time="11:00",
        description="Existing event",
        faculty_user_id=3002,
        created_by_user_id=club.coordinator_user_id,
    )
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/sessions",
        {
            "venue": "Auditorium",
            "date": "2026-12-03",
            "start_time": "10:30",
            "end_time": "11:30",
            "description": "Overlapping session",
        },
        format="json",
    )

    assert response.status_code == 409
    assert not ClubSession.objects.exists()
    assert ClubEvent.objects.get(pk=existing.pk).name == "Existing event"


def test_tc032_zero_amount_budget_request_with_file_is_tracked(stub_iam):
    """test_id=TC-032; source_id=Problem Statement §4.1 In Scope; §6 Business Constraints — club budget-request submission, non-negative amount, and required supporting file"""
    club = _club()
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/budgets",
        {
            "amount": "0",
            "purpose": "Equipment",
            "description": "Club equipment",
            "supporting_file": SimpleUploadedFile("quote.txt", b"quote"),
        },
        format="multipart",
    )

    assert response.status_code == 201
    request = BudgetRequest.objects.get(pk=response.json()["id"])
    assert request.amount == 0
    assert request.status == "open"
    assert request.supporting_file.storage.exists(request.supporting_file.name)


def test_tc033_negative_budget_amount_is_rejected(stub_iam):
    """test_id=TC-033; source_id=Problem Statement §6 Business Constraints — club budget amounts must be non-negative"""
    club = _club()
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/budgets",
        {
            "amount": "-1",
            "purpose": "Equipment",
            "description": "Club equipment",
            "supporting_file": SimpleUploadedFile("quote.txt", b"quote"),
        },
        format="multipart",
    )

    assert response.status_code == 400
    assert not BudgetRequest.objects.exists()


def test_tc034_budget_request_requires_supporting_file(stub_iam):
    """test_id=TC-034; source_id=Problem Statement §6 Business Constraints — budget requests must include the required supporting file"""
    club = _club()
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/budgets",
        {"amount": "0", "purpose": "Equipment", "description": "Club equipment"},
        format="multipart",
    )

    assert response.status_code == 400
    assert not BudgetRequest.objects.exists()


def test_tc035_event_report_and_required_file_are_stored(stub_iam):
    """test_id=TC-035; source_id=Problem Statement §4.1 In Scope; §6 Business Constraints — club event-report submission and required report/details file"""
    club = _club()
    _person(4101)
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/reports",
        {
            "student_incharge_user_id": 4101,
            "event_name": "Robot showcase",
            "event_at": timezone.now().isoformat(),
            "description": "Showcase report",
            "report_file": SimpleUploadedFile("report.txt", b"report contents"),
        },
        format="multipart",
    )

    assert response.status_code == 201
    report = ClubEventReport.objects.get(pk=response.json()["id"])
    assert report.report_file.storage.exists(report.report_file.name)


def test_tc036_event_report_without_required_file_is_rejected(stub_iam):
    """test_id=TC-036; source_id=Problem Statement §6 Business Constraints — club event reports must include the required report/details file"""
    club = _club()
    _person(4101)
    head = _client(stub_iam, user_id=club.coordinator_user_id)

    response = head.post(
        f"{ROOT}/clubs/{club.pk}/reports",
        {
            "student_incharge_user_id": 4101,
            "event_name": "Robot showcase",
            "event_at": timezone.now().isoformat(),
            "description": "Showcase report",
        },
        format="multipart",
    )

    assert response.status_code == 400
    assert not ClubEventReport.objects.exists()


def test_tc037_assigned_faculty_can_access_and_review_report(stub_iam):
    """test_id=TC-037; source_id=Problem Statement §3.5 Event Reporting; §8 Success Criteria — assigned Club Faculty Councillor can access and review reports for the assigned club"""
    club = _club()
    _person(4101)
    head = _client(stub_iam, user_id=club.coordinator_user_id)
    submitted = head.post(
        f"{ROOT}/clubs/{club.pk}/reports",
        {
            "student_incharge_user_id": 4101,
            "event_name": "Robot showcase",
            "event_at": timezone.now().isoformat(),
            "description": "Showcase report",
            "report_file": SimpleUploadedFile("report.txt", b"report contents"),
        },
        format="multipart",
    )
    assert submitted.status_code == 201
    faculty = _client(
        stub_iam,
        user_id=club.faculty_councillor_user_id,
        kind="faculty",
        role="faculty",
        permissions=FACULTY,
    )

    reports = faculty.get(f"{ROOT}/reports/assigned")
    downloaded = faculty.get(submitted.json()["download_url"])

    assert reports.status_code == 200
    assert reports.json()["results"][0]["event_name"] == "Robot showcase"
    assert downloaded.status_code == 200
    assert b"report contents" in b"".join(downloaded.streaming_content)
