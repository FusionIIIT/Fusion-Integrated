"""Real threads against the real database: things that must happen once."""
import threading
from datetime import timedelta

import pytest
from django.db import connection
from django.utils import timezone

from conftest import make_principal
from modules.gymkhana.models import Booking, Club, Membership, Vote
from modules.gymkhana.services import bookings, clubs, memberships, polls
from modules.gymkhana.tests.conftest import (
    COORD,
    PLAIN,
    STUDENT,
    STUDENT_ADMIN,
    make_club,
    people,
)

pytestmark = pytest.mark.django_db(transaction=True)
THREADS = 6


def race(fn):
    barrier = threading.Barrier(THREADS)
    results = []

    def run():
        barrier.wait()
        try:
            results.append(fn())
        except Exception as exc:  # noqa: BLE001 — every outcome is collected and asserted
            results.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=run) for _ in range(THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


@pytest.fixture
def directory(stub_iam):
    return stub_iam(users=people())


def test_br_gym_006_overlapping_bookings_at_once_yield_one(directory):
    from modules.gymkhana.services.venues import seed_venue_list
    club = make_club()
    seed_venue_list(names=["LHTC 101"], effective_from=timezone.now() - timedelta(days=1))
    head = make_principal(user_id=COORD, permissions=STUDENT, modules=("gymkhana",))
    day = timezone.localdate() + timedelta(days=1)
    starts = iter(["10:00", "10:15", "10:30", "10:45", "10:05", "10:20"])
    lock = threading.Lock()

    def book():
        with lock:
            start = next(starts)
        from datetime import time
        h, m = map(int, start.split(":"))
        return bookings.book_session(actor=head, club_id=club.pk, venue="LHTC 101", date=day,
                                     start_time=time(h, m), end_time=time(h + 1, m),
                                     description="d")

    from datetime import time
    # An earlier booking that day, so the venue-day row exists and only the lock can serialize.
    bookings.book_session(actor=head, club_id=club.pk, venue="LHTC 101", date=day,
                          start_time=time(7), end_time=time(8), description="early")
    race(book)
    assert Booking.objects.filter(venue_name="LHTC 101", date=day).count() == 2


def test_br_gym_009_duplicate_applications_at_once_yield_one(directory):
    club = make_club()
    student = make_principal(user_id=PLAIN, permissions=STUDENT, modules=("gymkhana",))
    race(lambda: memberships.apply(actor=student, club_id=club.pk, description="x"))
    assert Membership.objects.filter(club=club, user_id=PLAIN).count() == 1


def test_br_gym_015_double_votes_at_once_yield_one(directory):
    from modules.gymkhana.domain.rules import Target
    club = make_club()
    head = make_principal(user_id=COORD, permissions=STUDENT, modules=("gymkhana",))
    poll = polls.create_poll(actor=head, club_id=club.pk, title="t", description="d",
                             expires_on=timezone.localdate() + timedelta(days=1),
                             choices=["a", "b"], targets=[Target(2023, "CSE")])
    choice = poll.choices.first()
    voter = make_principal(user_id=PLAIN, permissions=STUDENT, modules=("gymkhana",))
    race(lambda: polls.cast_vote(actor=voter, poll_id=poll.pk, choice_id=choice.pk))
    assert Vote.objects.filter(poll=poll).count() == 1


def test_br_gym_004_approving_at_once_confirms_once(directory):
    from modules.gymkhana.models import AuditEvent
    pending = make_club("Pending", status="open")
    admin = make_principal(user_id=9001, permissions=STUDENT_ADMIN, modules=("gymkhana",),
                           kind="staff")
    race(lambda: clubs.approve_club(actor=admin, club_id=pending.pk))
    assert Club.objects.get(pk=pending.pk).status == "confirmed"
    assert AuditEvent.objects.filter(action="club.approved").count() == 1


def test_same_name_clubs_at_once_yield_one(stub_iam):
    users = people()
    stub_iam(users=users)
    admin = make_principal(user_id=9001, permissions=STUDENT_ADMIN, modules=("gymkhana",),
                           kind="staff")
    race(lambda: clubs.create_club(actor=admin, name="Chess", category="sports",
                                   description="d", coordinator_user_id=1003,
                                   co_coordinator_user_id=1004,
                                   faculty_councillor_user_id=2001))
    assert Club.objects.filter(name__iexact="chess").count() == 1


def test_membership_approval_at_once_is_recorded_once(directory):
    from modules.gymkhana.models import AuditEvent
    club = make_club()
    app = Membership.objects.create(club=club, user_id=PLAIN, description="x")
    head = make_principal(user_id=COORD, permissions=STUDENT, modules=("gymkhana",))
    race(lambda: memberships.approve_many(actor=head, ids=[app.pk]))
    assert AuditEvent.objects.filter(action="membership.approved").count() == 1
