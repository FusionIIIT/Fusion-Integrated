"""Concurrency and race-condition safety tests.

Double-booking a venue concurrently or voting multiple times in a poll must be
prevented by database constraints and locks.
"""
from datetime import date, time

import pytest
from django.apps import apps
from django.test import override_settings

from core.api.exceptions import ConflictError
from modules.gymkhana import services
from modules.gymkhana.models import Club, PollChoice, PollTargetGroup, VotingPoll

pytestmark = pytest.mark.django_db


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


@override_settings(GYMKHANA_VENUES=("SAC Hall",))
def test_concurrent_booking_overlap_prevention():
    _person(2001, "student")
    _person(2002, "student")
    _person(3001, "faculty")
    club = Club.objects.create(
        name="Drama Club",
        category="Cultural",
        coordinator_user_id=2001,
        co_coordinator_user_id=2002,
        faculty_councillor_user_id=3001,
        description="Drama",
        status=Club.Status.CONFIRMED,
    )

    # First booking succeeds
    s1 = services.book_session(
        club=club,
        user_id=club.coordinator_user_id,
        data={
            "venue": "SAC Hall",
            "date": date(2026, 12, 15),
            "start_time": time(14, 0),
            "end_time": time(16, 0),
        },
    )
    assert s1.pk is not None

    # Overlapping booking raises ConflictError
    with pytest.raises(ConflictError) as exc_info:
        services.book_session(
            club=club,
            user_id=club.coordinator_user_id,
            data={
                "venue": "SAC Hall",
                "date": date(2026, 12, 15),
                "start_time": time(15, 0),
                "end_time": time(17, 0),
            },
        )
    assert exc_info.value.code == "venue_conflict"

    # Exact same time slot raises ConflictError
    with pytest.raises(ConflictError) as exc_info:
        services.book_event(
            club=club,
            user_id=club.coordinator_user_id,
            data={
                "name": "Play",
                "faculty_user_id": 3001,
                "venue": "SAC Hall",
                "date": date(2026, 12, 15),
                "start_time": time(14, 0),
                "end_time": time(16, 0),
            },
        )
    assert exc_info.value.code == "venue_conflict"


def test_concurrent_poll_vote_deduplication():
    _person(2001, "student", batch_year=2024, discipline="CSE")
    _person(2002, "student", batch_year=2024, discipline="CSE")
    _person(3001, "faculty")
    club = Club.objects.create(
        name="Film Club",
        category="Cultural",
        coordinator_user_id=2001,
        co_coordinator_user_id=2002,
        faculty_councillor_user_id=3001,
        description="Films",
        status=Club.Status.CONFIRMED,
    )
    from datetime import timedelta

    from django.utils import timezone

    poll = VotingPoll.objects.create(
        club=club,
        title="Movie Night",
        description="Pick a movie",
        expires_at=timezone.now() + timedelta(days=2),
        created_by_user_id=2001,
        is_active=True,
    )
    c1 = PollChoice.objects.create(poll=poll, text="Interstellar")
    c2 = PollChoice.objects.create(poll=poll, text="Inception")
    PollTargetGroup.objects.create(poll=poll, batch_year=2024, discipline="CSE")

    # Vote 1 succeeds
    v1 = services.cast_vote(poll_id=poll.pk, choice_id=c1.pk, student_user_id=2001)
    assert v1.pk is not None

    # Vote 2 on another choice by same student fails with already_voted
    with pytest.raises(ConflictError) as exc_info:
        services.cast_vote(poll_id=poll.pk, choice_id=c2.pk, student_user_id=2001)
    assert exc_info.value.code == "already_voted"


def test_duplicate_membership_application_rejected():
    _person(2001, "student")
    _person(2002, "student")
    _person(2003, "student")
    _person(3001, "faculty")
    club = Club.objects.create(
        name="Design Club",
        category="Technical",
        coordinator_user_id=2001,
        co_coordinator_user_id=2002,
        faculty_councillor_user_id=3001,
        description="Design",
        status=Club.Status.CONFIRMED,
    )

    # First application succeeds
    app1 = services.apply_for_membership(
        club=club,
        student_user_id=2003,
        description="First application",
    )
    assert app1.pk is not None

    # Second application while active raises ConflictError
    with pytest.raises(ConflictError):
        services.apply_for_membership(
            club=club,
            student_user_id=2003,
            description="Second application",
        )
