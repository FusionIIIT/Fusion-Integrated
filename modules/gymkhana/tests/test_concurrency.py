"""Real threads on real connections: each of these must happen exactly once."""
import datetime
import threading

import pytest
from django.db import IntegrityError, connection

from core.api.exceptions import ConflictError
from modules.gymkhana.models import Club, ClubMembership, PollVote, VenueBooking, VenueDay
from modules.gymkhana.services.bookings import book_event, book_session
from modules.gymkhana.services.clubs import approve_club, create_club
from modules.gymkhana.services.memberships import apply_membership
from modules.gymkhana.services.polls import cast_vote
from modules.gymkhana.tests.support import (
    ADMIN,
    CO_HEAD,
    COUNCILLOR,
    HEAD,
    STUDENT,
    make_club,
    make_poll,
    people,
)

pytestmark = pytest.mark.django_db(transaction=True)
WORKERS = 8


def race(act):
    """Every worker released together; returns each outcome as 'ok' or the error's name."""
    barrier, outcomes = threading.Barrier(WORKERS), []

    def run(n):
        try:
            barrier.wait()
            act(n)
            outcomes.append("ok")
        except (ConflictError, IntegrityError) as exc:
            outcomes.append(type(exc).__name__)
        finally:
            connection.close()

    threads = [threading.Thread(target=run, args=(n,)) for n in range(WORKERS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return sorted(outcomes)


ONCE = sorted(["ok"] + [ConflictError.__name__] * (WORKERS - 1))


@pytest.mark.parametrize("day_in_use", [False, True])
def test_br_gym_006_one_slot_is_booked_once_across_sessions_and_events(stub_iam, day_in_use):
    people()
    club = make_club()
    if day_in_use:
        # Inserting the day's row already queues the first bookings; only later ones need the lock.
        VenueDay.objects.create(venue="Hall 1", booking_date=datetime.date(2027, 3, 1))
    when = {"venue": "Hall 1", "booking_date": datetime.date(2027, 3, 1),
            "start_time": datetime.time(10), "end_time": datetime.time(11)}

    def act(n):
        common = {"club_id": club.pk, "actor_id": HEAD, "description": "", **when}
        if n % 2:
            book_session(**common)
        else:
            book_event(**common, name="Talk", faculty_councillor_id=COUNCILLOR)

    assert race(act) == ONCE
    assert VenueBooking.objects.count() == 1


def test_br_gym_009_one_application_per_club(stub_iam):
    people()
    club = make_club()
    assert race(lambda n: apply_membership(club_id=club.pk, student_id=STUDENT)) == ONCE
    assert ClubMembership.objects.count() == 1


def test_br_gym_015_one_vote_and_one_tally_increment(stub_iam):
    people()
    poll = make_poll(make_club())
    choice = poll.choices.first()
    assert race(lambda n: cast_vote(
        poll_id=poll.pk, student_id=STUDENT, choice_id=choice.pk)) == ONCE
    choice.refresh_from_db()
    assert (PollVote.objects.count(), choice.vote_count) == (1, 1)


def test_afr_gym_028_different_voters_never_lose_an_increment(stub_iam):
    people()
    poll = make_poll(make_club())
    choice = poll.choices.first()
    assert race(lambda n: cast_vote(
        poll_id=poll.pk, student_id=1000 + n, choice_id=choice.pk)) == ["ok"] * WORKERS
    choice.refresh_from_db()
    assert choice.vote_count == WORKERS


def test_br_gym_004_a_club_is_confirmed_once(stub_iam):
    people()
    club = make_club(status="open")
    assert race(lambda n: approve_club(
        club_id=club.pk, approver_id=ADMIN, roles=["student_admin"])) == ONCE


def test_one_club_per_name(stub_iam):
    people()
    assert race(lambda n: create_club(
        name="Chess Club", category="sports", description="", coordinator_id=HEAD,
        co_coordinator_id=CO_HEAD, faculty_councillor_id=COUNCILLOR, creator_id=ADMIN,
    )) == ONCE
    assert Club.objects.count() == 1
