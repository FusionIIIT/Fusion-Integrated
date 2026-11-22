"""Tests for Gymkhana business services (UC-GYM-001 through UC-GYM-011)."""
from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from fusion_auth.client import UserRef as IamUserRef
from modules.gymkhana.domain.exceptions import (
    InvalidPollChoicesError,
    InvalidTransition,
    InvalidVoteChoiceError,
)
from modules.gymkhana.models import (
    Club,
    ClubLeadershipHistory,
)
from modules.gymkhana.services.budgets import submit_budget_request
from modules.gymkhana.services.clubs import approve_club, change_leadership, create_club
from modules.gymkhana.services.memberships import apply_membership, approve_membership
from modules.gymkhana.services.polls import cast_vote, create_poll
from modules.gymkhana.services.reports import submit_event_report


@pytest.fixture
def stub_directory(stub_iam):
    """Install common student and faculty users in the fake IAM directory."""
    stub_iam(
        users={
            101: IamUserRef(user_id=101, username="u101", display_name="Alice", kind="student", discipline="CSE"),
            102: IamUserRef(user_id=102, username="u102", display_name="Bob", kind="student", discipline="CSE"),
            103: IamUserRef(user_id=103, username="u103", display_name="Charlie", kind="student", discipline="ECE"),
            104: IamUserRef(user_id=104, username="u104", display_name="Diana", kind="student", discipline="ECE"),
            201: IamUserRef(user_id=201, username="u201", display_name="Student 1", kind="student", discipline="CSE", batch_year=2024),
            202: IamUserRef(user_id=202, username="u202", display_name="Student 2", kind="student", discipline="ME", batch_year=2023),
            501: IamUserRef(user_id=501, username="u501", display_name="Dr. Smith", kind="faculty", discipline="CSE"),
            502: IamUserRef(user_id=502, username="u502", display_name="Dr. Jones", kind="faculty", discipline="ECE"),
        }
    )


@pytest.fixture
def confirmed_club(stub_directory):
    return Club.objects.create(
        name="Robotics Club",
        category="Technical",
        description="Build bots",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=501,
        status="confirmed",
    )


# ---------------------------------------------------------------------------
# Club Services Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_create_club_success(stub_directory):
    club = create_club(
        name="Coding Club",
        category="Technical",
        description="Competitive programming",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=501,
        changed_by_user_id=1,
    )
    assert club.pk is not None
    assert club.status == "open"
    assert club.name == "Coding Club"

    # Verify initial tenure in ClubLeadershipHistory
    history = ClubLeadershipHistory.objects.filter(club=club)
    assert history.count() == 1
    h = history.first()
    assert h.coordinator_id == 101
    assert h.co_coordinator_id == 102
    assert h.effective_to is None
    assert h.changed_by_user_id == 1


@pytest.mark.django_db
def test_create_club_validations(stub_directory):
    # Same coordinator and co-coordinator
    with pytest.raises(BadRequestError) as exc:
        create_club(
            name="Invalid Club 1",
            category="Technical",
            description="desc",
            coordinator_id=101,
            co_coordinator_id=101,
            faculty_councillor_id=501,
            changed_by_user_id=1,
        )
    assert exc.value.code == "duplicate_coordinators"

    # Faculty passed as coordinator
    with pytest.raises(BadRequestError) as exc:
        create_club(
            name="Invalid Club 2",
            category="Technical",
            description="desc",
            coordinator_id=501,
            co_coordinator_id=102,
            faculty_councillor_id=501,
            changed_by_user_id=1,
        )
    assert exc.value.code == "invalid_coordinator"

    # Student passed as faculty councillor
    with pytest.raises(BadRequestError) as exc:
        create_club(
            name="Invalid Club 3",
            category="Technical",
            description="desc",
            coordinator_id=101,
            co_coordinator_id=102,
            faculty_councillor_id=103,
            changed_by_user_id=1,
        )
    assert exc.value.code == "invalid_faculty_councillor"

    # Invalid category
    with pytest.raises(BadRequestError) as exc:
        create_club(
            name="Invalid Club 4",
            category="Academics",
            description="desc",
            coordinator_id=101,
            co_coordinator_id=102,
            faculty_councillor_id=501,
            changed_by_user_id=1,
        )
    assert exc.value.code == "invalid_category"


@pytest.mark.django_db
def test_create_club_duplicate_name(stub_directory):
    create_club(
        name="Music Club",
        category="Cultural",
        description="Music",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=501,
        changed_by_user_id=1,
    )
    with pytest.raises(ConflictError) as exc:
        create_club(
            name="Music Club",
            category="Cultural",
            description="Another music club",
            coordinator_id=103,
            co_coordinator_id=104,
            faculty_councillor_id=501,
            changed_by_user_id=1,
        )
    assert exc.value.code == "club_name_exists"


@pytest.mark.django_db
def test_approve_club(stub_directory):
    club = create_club(
        name="Dance Club",
        category="Cultural",
        description="Dance",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=501,
        changed_by_user_id=1,
    )
    approved = approve_club(club_id=club.id, actor_user_id=1)
    assert approved.status == "confirmed"

    # Double approve raises InvalidTransition
    with pytest.raises(InvalidTransition):
        approve_club(club_id=club.id, actor_user_id=1)

    # Nonexistent club raises NotFoundError
    with pytest.raises(NotFoundError) as exc:
        approve_club(club_id=9999, actor_user_id=1)
    assert exc.value.code == "club_not_found"


@pytest.mark.django_db
def test_change_leadership(stub_directory, confirmed_club):
    # Initial tenure row
    ClubLeadershipHistory.objects.create(
        club=confirmed_club,
        coordinator_id=101,
        co_coordinator_id=102,
        effective_from=timezone.now(),
        effective_to=None,
        changed_by_user_id=1,
    )

    # Coordinator 101 changes leadership to 103, 104
    updated_club = change_leadership(
        club=confirmed_club,
        new_coordinator_id=103,
        new_co_coordinator_id=104,
        changed_by_user_id=101,
    )
    assert updated_club.coordinator_id == 103
    assert updated_club.co_coordinator_id == 104

    # Verify previous tenure is closed and new tenure active
    history = list(ClubLeadershipHistory.objects.filter(club=confirmed_club).order_by("id"))
    assert len(history) == 2
    assert history[0].effective_to is not None
    assert history[1].coordinator_id == 103
    assert history[1].co_coordinator_id == 104
    assert history[1].effective_to is None
    assert history[1].changed_by_user_id == 101

    # Unauthorized student attempting to change leadership fails
    with pytest.raises(ConflictError) as exc:
        change_leadership(
            club=updated_club,
            new_coordinator_id=101,
            new_co_coordinator_id=102,
            changed_by_user_id=999,
        )
    assert exc.value.code == "not_club_head"


# ---------------------------------------------------------------------------
# Membership Services Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_apply_and_approve_membership(stub_directory, confirmed_club):
    # Student 201 applies -> status is "open" (BW-GYM-01)
    membership = apply_membership(club=confirmed_club, student_id=201)
    assert membership.status == "open"
    assert membership.student_id == 201
    assert membership.club == confirmed_club

    # Duplicate application rejected
    with pytest.raises(ConflictError) as exc:
        apply_membership(club=confirmed_club, student_id=201)
    assert exc.value.code == "duplicate_membership_application"

    # Unauthorized user cannot approve
    with pytest.raises(ConflictError) as exc:
        approve_membership(membership_id=membership.id, actor_user_id=999)
    assert exc.value.code == "not_club_head"

    # Coordinator 101 approves
    approved = approve_membership(membership_id=membership.id, actor_user_id=101)
    assert approved.status == "confirmed"

    # Approving already confirmed membership raises InvalidTransition
    with pytest.raises(InvalidTransition):
        approve_membership(membership_id=membership.id, actor_user_id=101)


@pytest.mark.django_db
def test_apply_membership_unconfirmed_club(stub_directory):
    open_club = Club.objects.create(
        name="Unconfirmed Club",
        category="Sports",
        description="Pending",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=501,
        status="open",
    )
    with pytest.raises(ConflictError) as exc:
        apply_membership(club=open_club, student_id=201)
    assert exc.value.code == "club_not_confirmed"


# ---------------------------------------------------------------------------
# Poll Services Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_create_and_vote_poll(stub_directory, confirmed_club):
    future = timezone.now() + datetime.timedelta(days=3)
    poll = create_poll(
        club=confirmed_club,
        title="Club Mascot",
        description="Choose mascot",
        expires_at=future,
        choices=["Robot", "Eagle", "Falcon"],
        targets=[{"batch_year": 2024, "discipline": "CSE"}],
        user_id=101,
    )
    assert poll.status == "active"
    assert poll.choices.count() == 3
    assert poll.targets.count() == 1

    choice_robot = poll.choices.get(text="Robot")

    # Student 201 (batch 2024, CSE) votes
    vote = cast_vote(poll=poll, choice_id=choice_robot.id, student_id=201)
    assert vote.poll == poll
    assert vote.choice == choice_robot
    assert vote.student_id == 201

    # Duplicate vote rejected
    with pytest.raises(ConflictError) as exc:
        cast_vote(poll=poll, choice_id=choice_robot.id, student_id=201)
    assert exc.value.code == "duplicate_vote"

    # Student 202 (batch 2023, ME) not targeted rejected
    with pytest.raises(ConflictError) as exc:
        cast_vote(poll=poll, choice_id=choice_robot.id, student_id=202)
    assert exc.value.code == "student_not_targeted"


@pytest.mark.django_db
def test_poll_validations(stub_directory, confirmed_club):
    # Past expiry time
    past = timezone.now() - datetime.timedelta(days=1)
    with pytest.raises(BadRequestError) as exc:
        create_poll(
            club=confirmed_club,
            title="Past Poll",
            description="desc",
            expires_at=past,
            choices=["A", "B"],
            targets=[{"batch_year": 2024}],
            user_id=101,
        )
    assert exc.value.code == "invalid_expiry_time"

    # Fewer than 2 choices
    future = timezone.now() + datetime.timedelta(days=2)
    with pytest.raises(InvalidPollChoicesError):
        create_poll(
            club=confirmed_club,
            title="Single Choice",
            description="desc",
            expires_at=future,
            choices=["A"],
            targets=[{"batch_year": 2024}],
            user_id=101,
        )

    # Empty targets
    with pytest.raises(BadRequestError) as exc:
        create_poll(
            club=confirmed_club,
            title="No Targets",
            description="desc",
            expires_at=future,
            choices=["A", "B"],
            targets=[],
            user_id=101,
        )
    assert exc.value.code == "empty_targets"

    # Choice from different poll rejected
    poll1 = create_poll(
        club=confirmed_club,
        title="Poll 1",
        description="desc",
        expires_at=future,
        choices=["Option 1", "Option 2"],
        targets=[{"batch_year": 2024}],
        user_id=101,
    )
    poll2 = create_poll(
        club=confirmed_club,
        title="Poll 2",
        description="desc",
        expires_at=future,
        choices=["Option X", "Option Y"],
        targets=[{"batch_year": 2024}],
        user_id=101,
    )
    choice_from_poll2 = poll2.choices.first()
    with pytest.raises(InvalidVoteChoiceError):
        cast_vote(poll=poll1, choice_id=choice_from_poll2.id, student_id=201)


# ---------------------------------------------------------------------------
# Budget Services Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_submit_budget_request(stub_directory, confirmed_club):
    valid_drive_url = "https://drive.google.com/file/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/view"

    # Coordinator submits request
    req = submit_budget_request(
        club=confirmed_club,
        amount=15000,
        purpose="Robotics Kit",
        description="Sensors and microcontrollers",
        supporting_file_url=valid_drive_url,
        user_id=101,
    )
    assert req.amount == Decimal("15000")
    assert req.status == "open"
    assert req.supporting_file_id == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"

    # Negative amount rejected
    with pytest.raises(BadRequestError) as exc:
        submit_budget_request(
            club=confirmed_club,
            amount=-500,
            purpose="Invalid",
            description="Negative amount",
            supporting_file_url=valid_drive_url,
            user_id=101,
        )
    assert exc.value.code == "negative_amount"

    # Invalid drive link rejected
    with pytest.raises(BadRequestError):
        submit_budget_request(
            club=confirmed_club,
            amount=500,
            purpose="Invalid link",
            description="Bad URL",
            supporting_file_url="https://notdrive.com/file/123",
            user_id=101,
        )

    # Unauthorized user rejected
    with pytest.raises(ConflictError) as exc:
        submit_budget_request(
            club=confirmed_club,
            amount=500,
            purpose="Unauthorized",
            description="Non-head",
            supporting_file_url=valid_drive_url,
            user_id=999,
        )
    assert exc.value.code == "not_club_head"


# ---------------------------------------------------------------------------
# Event Report Services Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_submit_event_report(stub_directory, confirmed_club):
    valid_drive_url = "https://drive.google.com/file/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/view"

    report = submit_event_report(
        club=confirmed_club,
        event_name="RoboWars 2026",
        event_date=datetime.date(2026, 11, 15),
        event_time=datetime.time(10, 0),
        description="Inter-college battle",
        student_incharge_id=201,
        report_file_url=valid_drive_url,
        user_id=101,
    )
    assert report.event_name == "RoboWars 2026"
    assert report.event_date == datetime.date(2026, 11, 15)
    assert report.student_incharge_id == 201
    assert report.report_file_id == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
    assert report.submitted_by_user_id == 101

    # Non-student incharge rejected
    with pytest.raises(BadRequestError) as exc:
        submit_event_report(
            club=confirmed_club,
            event_name="RoboWars 2026",
            event_date=datetime.date(2026, 11, 15),
            event_time=datetime.time(10, 0),
            description="Inter-college battle",
            student_incharge_id=501,  # faculty member
            report_file_url=valid_drive_url,
            user_id=101,
        )
    assert exc.value.code == "invalid_student_incharge"

    # Non-head submitter rejected
    with pytest.raises(ConflictError) as exc:
        submit_event_report(
            club=confirmed_club,
            event_name="RoboWars 2026",
            event_date=datetime.date(2026, 11, 15),
            event_time=datetime.time(10, 0),
            description="Inter-college battle",
            student_incharge_id=201,
            report_file_url=valid_drive_url,
            user_id=999,
        )
    assert exc.value.code == "not_club_head"
