"""Comprehensive coverage tests targeting service/view/serializer edge cases and error paths."""
from datetime import date, time, timedelta
from unittest.mock import patch

import pytest
from django.apps import apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.gymkhana import registry, services
from modules.gymkhana.models import (
    Club,
    MembershipApplication,
    NotificationOutbox,
    PollChoice,
    PollTargetGroup,
    VotingPoll,
)

pytestmark = pytest.mark.django_db

ROOT = "/api/v1/gymkhana"
STUDENT_PERMS = tuple(registry.ROLE_GRANTS["student"])
ADMIN_PERMS = tuple(registry.ROLE_GRANTS["Student Admin"])
FACULTY_PERMS = tuple(registry.ROLE_GRANTS["faculty"])


def _set_user(stub_iam, *, user_id, kind="student", role=None, permissions=None):
    role = role or kind
    grants = permissions if permissions is not None else registry.ROLE_GRANTS.get(role, ())
    stub_iam(make_session(
        user_id=user_id,
        kind=kind,
        roles=(role,),
        active_role=role,
        modules=("gymkhana",),
        permissions=grants,
    ))


def _person(user_id, kind, *, batch_year=2024, discipline="CSE"):
    user_ref_cls = apps.get_model("directory", "UserRef")
    return user_ref_cls.objects.create(
        user_id=user_id,
        username=f"u{user_id}",
        display_name=f"Person {user_id}",
        kind=kind,
        batch_year=batch_year if kind == "student" else None,
        discipline=discipline if kind == "student" else "",
    )


def test_people_search_view(stub_iam):
    _person(101, "student")
    _person(102, "faculty")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    _set_user(stub_iam, user_id=101, permissions=STUDENT_PERMS)

    # Empty query or invalid kind returns empty list
    assert client.get(f"{ROOT}/people?kind=unknown&q=Per").json()["results"] == []
    assert client.get(f"{ROOT}/people?kind=student&q=P").json()["results"] == []

    # Valid query
    res = client.get(f"{ROOT}/people?kind=student&q=Person").json()
    assert len(res["results"]) >= 1


def test_venue_list_view(stub_iam):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    _set_user(stub_iam, user_id=2001, permissions=STUDENT_PERMS)
    res = client.get(f"{ROOT}/venues")
    assert res.status_code == 200
    assert "results" in res.json()


def test_club_validation_errors():
    _person(2001, "student")
    _person(2002, "student")
    _person(3001, "faculty")

    # Same person as coordinator and co-coordinator
    with pytest.raises(ConflictError) as exc_info:
        services.validate_leaders(2001, 2001)
    assert exc_info.value.code == "duplicate_leader"

    # Confirmed club not found
    with pytest.raises(NotFoundError):
        services.confirmed_club(99999)

    # Require club head raises PermissionDeniedError for non-head
    club = Club.objects.create(
        name="Art Club",
        category="Cultural",
        coordinator_user_id=2001,
        co_coordinator_user_id=2002,
        faculty_councillor_user_id=3001,
        status=Club.Status.CONFIRMED,
    )
    with pytest.raises(PermissionDeniedError):
        services.require_club_head(club, 9999)

    # Approve club when already confirmed raises ConflictError
    with pytest.raises(ConflictError):
        services.approve_club(club_id=club.pk)

    # Change leadership with duplicate leader
    with pytest.raises(ConflictError):
        services.change_leadership(club=club, coordinator_user_id=2001, co_coordinator_user_id=2001)

    # Unconfigured venue raises ConflictError
    with pytest.raises(ConflictError):
        services.book_session(
            club=club,
            user_id=2001,
            data={
                "venue": "Nonexistent Stadium",
                "date": date(2026, 12, 1),
                "start_time": time(10, 0),
                "end_time": time(12, 0),
            },
        )


def test_membership_and_poll_edge_cases():
    _person(2001, "student", batch_year=2024, discipline="CSE")
    _person(2002, "student", batch_year=2024, discipline="ECE")
    _person(3001, "faculty")

    open_club = Club.objects.create(
        name="Unconfirmed Club",
        category="Technical",
        coordinator_user_id=2001,
        co_coordinator_user_id=2002,
        faculty_councillor_user_id=3001,
        status=Club.Status.OPEN,
    )

    # Applying to unconfirmed club raises ConflictError
    with pytest.raises(ConflictError):
        services.apply_for_membership(club=open_club, student_user_id=2001, description="test")

    # Confirm the club
    open_club.status = Club.Status.CONFIRMED
    open_club.save()

    app = services.apply_for_membership(club=open_club, student_user_id=2002, description="test")
    assert app.status == MembershipApplication.Status.OPEN

    # Approve membership
    approved = services.approve_membership(
        application_id=app.pk,
        club=open_club,
        actor_user_id=2001,
        remarks="Welcome!",
    )
    assert approved.status == MembershipApplication.Status.CONFIRMED

    # Approving already approved membership raises ConflictError
    with pytest.raises(ConflictError):
        services.approve_membership(
            application_id=app.pk,
            club=open_club,
            actor_user_id=2001,
            remarks="Again",
        )

    # Poll expired / closed
    poll = VotingPoll.objects.create(
        club=open_club,
        title="Expired Poll",
        expires_at=timezone.now() - timedelta(days=1),
        created_by_user_id=2001,
        is_active=True,
    )
    c1 = PollChoice.objects.create(poll=poll, text="Old Choice")
    PollTargetGroup.objects.create(poll=poll, batch_year=2024, discipline="CSE")

    with pytest.raises(ConflictError) as exc:
        services.cast_vote(poll_id=poll.pk, choice_id=c1.pk, student_user_id=2001)
    assert exc.value.code == "poll_closed"

    # Inactive poll
    poll.expires_at = timezone.now() + timedelta(days=2)
    poll.is_active = False
    poll.save()
    with pytest.raises(ConflictError) as exc:
        services.cast_vote(poll_id=poll.pk, choice_id=c1.pk, student_user_id=2001)
    assert exc.value.code == "poll_closed"

    # Nonexistent choice in poll
    poll.is_active = True
    poll.save()
    with pytest.raises(NotFoundError):
        services.cast_vote(poll_id=poll.pk, choice_id=99999, student_user_id=2001)

    # Faculty reports for councillor
    club_ids = services.faculty_report_club_ids(3001)
    assert open_club.pk in club_ids


def test_views_membership_mine_and_session_list(stub_iam):
    _person(2001, "student")
    _person(2002, "student")
    _person(3001, "faculty")
    club = Club.objects.create(
        name="Dance Club",
        category="Cultural",
        coordinator_user_id=2001,
        co_coordinator_user_id=2002,
        faculty_councillor_user_id=3001,
        status=Club.Status.CONFIRMED,
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    _set_user(stub_iam, user_id=2001, permissions=STUDENT_PERMS)

    # Membership mine endpoint
    res = client.get(f"{ROOT}/memberships/mine")
    assert res.status_code == 200

    # Sessions list endpoint
    res = client.get(f"{ROOT}/clubs/{club.pk}/sessions")
    assert res.status_code == 200

    # Events list endpoint
    res = client.get(f"{ROOT}/clubs/{club.pk}/events")
    assert res.status_code == 200

    # Budgets list endpoint
    res = client.get(f"{ROOT}/clubs/{club.pk}/budgets")
    assert res.status_code == 200

    # Reports list endpoint
    res = client.get(f"{ROOT}/clubs/{club.pk}/reports")
    assert res.status_code == 200

    # Leadership update endpoint
    res = client.post(f"{ROOT}/clubs/{club.pk}/leadership", {
        "coordinator_user_id": 2002,
        "co_coordinator_user_id": 2001,
    }, format="json")
    assert res.status_code == 200
    club.refresh_from_db()
    assert club.coordinator_user_id == 2002


def test_attachment_download_edge_cases(stub_iam):
    _person(2001, "student")
    _person(2002, "student")
    _person(3001, "faculty")
    Club.objects.create(
        name="Chess Club",
        category="Technical",
        coordinator_user_id=2001,
        co_coordinator_user_id=2002,
        faculty_councillor_user_id=3001,
        status=Club.Status.CONFIRMED,
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    _set_user(stub_iam, user_id=2001, permissions=STUDENT_PERMS)

    # Unsupported kind
    res = client.get(f"{ROOT}/files/unknown/1")
    assert res.status_code == 404

    # Nonexistent id
    res = client.get(f"{ROOT}/files/budget/99999")
    assert res.status_code == 404

    res = client.get(f"{ROOT}/files/report/99999")
    assert res.status_code == 404

    res = client.get(f"{ROOT}/files/session/99999")
    assert res.status_code == 404

    res = client.get(f"{ROOT}/files/event/99999")
    assert res.status_code == 404


def test_notification_delivery_timeout_recovery_and_network_error(stub_iam):
    from fusion_auth.client import UserRef as IamUser
    stub_iam(users={
        7001: IamUser(
            user_id=7001,
            username="u7001",
            display_name="User 7001",
            kind="student",
            email="u7001@test.invalid",
        ),
    })

    # Outbox item stuck in SENDING past CLAIM_TIMEOUT
    outbox = NotificationOutbox.objects.create(
        recipient_user_id=7001,
        topic="test.stuck",
        dedupe_key="stuck-1",
        subject="Stuck",
        body="Stuck body",
        status=NotificationOutbox.Status.SENDING,
        claimed_at=timezone.now() - timedelta(minutes=15),
    )

    # Mock send_mail raising OSError (network failure)
    with patch("modules.gymkhana.services.notifications.send_mail", side_effect=OSError("Network down")):
        report = services.deliver_pending(limit=10)
        assert report["failed"] == 1

    outbox.refresh_from_db()
    assert outbox.status == NotificationOutbox.Status.FAILED
    assert "Network down" in outbox.last_error

    # Empty outbox delivery returns 0
    NotificationOutbox.objects.all().delete()
    assert services.deliver_pending()["sent"] == 0


def test_serializer_validators():
    from modules.gymkhana.api import serializers as s

    # ActivitySerializer end time before start time
    activity = s.ActivitySerializer(data={
        "venue": "Auditorium",
        "date": "2026-12-01",
        "start_time": "18:00:00",
        "end_time": "17:00:00",
        "description": "Session description",
    })
    assert not activity.is_valid()
    assert "end_time" in activity.errors

    # ActivitySerializer invalid venue
    activity_venue = s.ActivitySerializer(data={
        "venue": "Mars Ground",
        "date": "2026-12-01",
        "start_time": "16:00:00",
        "end_time": "17:00:00",
        "description": "Session description",
    })
    assert not activity_venue.is_valid()
    assert "venue" in activity_venue.errors

    # ActivitySerializer oversized poster
    big_file = SimpleUploadedFile("huge.png", b"x" * (11 * 1024 * 1024))
    activity_file = s.ActivitySerializer(data={
        "venue": "Auditorium",
        "date": "2026-12-01",
        "start_time": "16:00:00",
        "end_time": "17:00:00",
        "poster": big_file,
    })
    assert not activity_file.is_valid()
    assert "poster" in activity_file.errors

    # PollTargetGroupSerializer blank discipline
    tg = s.PollTargetGroupSerializer(data={"batch_year": 2024, "discipline": "   "})
    assert not tg.is_valid()
    assert "discipline" in tg.errors

    # PollCreateSerializer with duplicate choices and blank choice
    poll_dup = s.PollCreateSerializer(data={
        "club_id": 1,
        "title": "Dup choices",
        "expires_at": "2026-12-31T23:59:59+05:30",
        "choices": ["Choice 1", "Choice 1"],
        "target_groups": [{"batch_year": 2024, "discipline": "CSE"}],
    })
    assert not poll_dup.is_valid()
    assert "choices" in poll_dup.errors

    poll_blank = s.PollCreateSerializer(data={
        "club_id": 1,
        "title": "Blank choice",
        "expires_at": "2026-12-31T23:59:59+05:30",
        "choices": ["Choice 1", "   "],
        "target_groups": [{"batch_year": 2024, "discipline": "CSE"}],
    })
    assert not poll_blank.is_valid()
    assert "choices" in poll_blank.errors

    # PollCreateSerializer duplicate target groups
    poll_dup_tg = s.PollCreateSerializer(data={
        "club_id": 1,
        "title": "Dup TG",
        "expires_at": "2026-12-31T23:59:59+05:30",
        "choices": ["Choice A", "Choice B"],
        "target_groups": [
            {"batch_year": 2024, "discipline": "CSE"},
            {"batch_year": 2024, "discipline": "CSE"},
        ],
    })
    assert not poll_dup_tg.is_valid()
    assert "target_groups" in poll_dup_tg.errors

    # BudgetRequestSerializer negative amount and oversized file
    budget_neg = s.BudgetRequestSerializer(data={
        "amount": "-500",
        "purpose": "Negative",
        "description": "Neg",
    })
    assert not budget_neg.is_valid()
    assert "amount" in budget_neg.errors

    budget_big = s.BudgetRequestSerializer(data={
        "amount": "500",
        "purpose": "Big file",
        "description": "Big",
        "supporting_file": big_file,
    })
    assert not budget_big.is_valid()
    assert "supporting_file" in budget_big.errors

