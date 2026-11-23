import threading
from datetime import date, time, timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.directory.models import UserRef
from modules.gymkhana.models.club import Club, ClubLeadership
from modules.gymkhana.services.bookings import book_session
from modules.gymkhana.services.memberships import apply_membership
from modules.gymkhana.services.polls import cast_vote, create_poll

pytestmark = pytest.mark.django_db(transaction=True)


def test_concurrent_venue_booking_barrier():
    club = Club.objects.create(
        name="Concurrent Club",
        category="Sports",
        faculty_councillor_id=201,
        status="confirmed",
    )
    ClubLeadership.objects.create(
        club=club,
        student_id=101,
        role="coordinator",
        is_current=True,
    )
    barrier = threading.Barrier(2)
    outcomes = []

    def attempt():
        barrier.wait()
        try:
            book_session(
                club_id=club.id,
                acting_user_id=101,
                title="Concurrent",
                venue="CC1",
                booking_date=date.today() + timedelta(days=20),
                start_time=time(10, 0),
                end_time=time(12, 0),
            )
            outcomes.append("created")
        except (ConflictError, PermissionDeniedError):
            outcomes.append("conflict")

    threads = [threading.Thread(target=attempt) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert outcomes.count("created") == 1
    assert outcomes.count("conflict") == 1


def test_concurrent_duplicate_membership_application():
    club = Club.objects.create(
        name="Concurrent Membership",
        category="Cultural",
        faculty_councillor_id=201,
        status="confirmed",
    )
    barrier = threading.Barrier(2)
    outcomes = []

    def attempt():
        barrier.wait()
        try:
            apply_membership(club_id=club.id, student_id=103, remarks="")
            outcomes.append("created")
        except (ConflictError, IntegrityError):
            outcomes.append("conflict")

    threads = [threading.Thread(target=attempt) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert outcomes.count("created") == 1
    assert outcomes.count("conflict") == 1


def test_concurrent_duplicate_poll_vote():
    UserRef.objects.create(
        user_id=103,
        username="s103",
        display_name="Student",
        kind="student",
        batch_year=2023,
        discipline="CSE",
    )
    club = Club.objects.create(
        name="Concurrent Poll",
        category="Sports",
        faculty_councillor_id=201,
        status="confirmed",
    )
    ClubLeadership.objects.create(
        club=club,
        student_id=101,
        role="coordinator",
        is_current=True,
    )
    poll = create_poll(
        club_id=club.id,
        acting_user_id=101,
        title="Choice",
        description="",
        target_batches=["2023"],
        target_branches=["CSE"],
        expires_at=timezone.now() + timedelta(days=2),
        choices=["A", "B"],
    )
    choice = poll.choices.first()
    barrier = threading.Barrier(2)
    outcomes = []

    def attempt():
        barrier.wait()
        try:
            cast_vote(poll_id=poll.id, student_id=103, choice_id=choice.id)
            outcomes.append("created")
        except (ConflictError, PermissionDeniedError, IntegrityError):
            outcomes.append("conflict")

    threads = [threading.Thread(target=attempt) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert outcomes.count("created") == 1
    assert outcomes.count("conflict") == 1
