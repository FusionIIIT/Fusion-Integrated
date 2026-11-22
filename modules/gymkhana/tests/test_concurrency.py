"""Tests for VenueDayLock concurrency engine and cross-type slot exclusivity (BR-GYM-006)."""
from __future__ import annotations

import datetime

import pytest

from core.api.exceptions import ConflictError
from modules.gymkhana.models import Booking, Club, VenueDayLock
from modules.gymkhana.services.bookings import acquire_venue_day_lock, book_event, book_session


@pytest.fixture
def confirmed_club():
    return Club.objects.create(
        name="Robotics Club",
        category="Technical",
        description="Build bots",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=501,
        status="confirmed",
    )


@pytest.fixture
def open_club():
    return Club.objects.create(
        name="New Club",
        category="Cultural",
        description="Pending club",
        coordinator_id=103,
        co_coordinator_id=104,
        faculty_councillor_id=501,
        status="open",
    )


@pytest.mark.django_db
def test_venue_day_lock_persistence_and_reuse():
    today = datetime.date(2026, 12, 1)
    lock1 = acquire_venue_day_lock("SAC", today)
    assert lock1.venue == "SAC"
    assert lock1.date == today
    assert VenueDayLock.objects.filter(venue="SAC", date=today).count() == 1

    # Second acquisition returns the same persistent anchor without error
    lock2 = acquire_venue_day_lock("SAC", today)
    assert lock2.id == lock1.id
    assert VenueDayLock.objects.filter(venue="SAC", date=today).count() == 1


@pytest.mark.django_db
def test_cross_type_slot_collision_session_and_event(confirmed_club, stub_iam, user_ref):
    stub_iam(users={501: user_ref(501, name="Dr. Smith", kind="faculty")})
    booking_date = datetime.date(2026, 12, 5)

    # 1. Book session from 10:00 to 12:00
    session1 = book_session(
        club=confirmed_club,
        venue="SAC",
        date=booking_date,
        start_time=datetime.time(10, 0),
        end_time=datetime.time(12, 0),
        description="Morning Robotics Session",
        user_id=101,
    )
    assert session1.booking_type == "session"
    assert Booking.objects.count() == 1

    # 2. Collision: Session overlapping 11:00 to 13:00 -> ConflictError
    with pytest.raises(ConflictError) as exc_info:
        book_session(
            club=confirmed_club,
            venue="SAC",
            date=booking_date,
            start_time=datetime.time(11, 0),
            end_time=datetime.time(13, 0),
            description="Overlapping Session",
            user_id=101,
        )
    assert exc_info.value.code == "venue_overlap"

    # 3. Cross-type collision: Event overlapping 11:30 to 13:30 -> ConflictError
    with pytest.raises(ConflictError) as exc_info:
        book_event(
            club=confirmed_club,
            venue="SAC",
            date=booking_date,
            start_time=datetime.time(11, 30),
            end_time=datetime.time(13, 30),
            name="RoboWars Exhibition",
            description="Robotics Event",
            user_id=102,
        )
    assert exc_info.value.code == "venue_overlap"

    # 4. Adjacent non-overlapping session from 12:00 to 14:00 on same venue succeeds
    session2 = book_session(
        club=confirmed_club,
        venue="SAC",
        date=booking_date,
        start_time=datetime.time(12, 0),
        end_time=datetime.time(14, 0),
        description="Afternoon Session",
        user_id=101,
    )
    assert session2.id is not None

    # 5. Overlapping time on DIFFERENT venue "L-101" succeeds
    session_other_venue = book_session(
        club=confirmed_club,
        venue="L-101",
        date=booking_date,
        start_time=datetime.time(10, 0),
        end_time=datetime.time(12, 0),
        description="Parallel Session in Lecture Hall",
        user_id=101,
    )
    assert session_other_venue.venue == "L-101"


@pytest.mark.django_db
def test_booking_authorization_and_club_status(confirmed_club, open_club):
    booking_date = datetime.date(2026, 12, 6)

    # Actor not coordinator or co-coordinator
    with pytest.raises(ConflictError) as exc_info:
        book_session(
            club=confirmed_club,
            venue="SAC",
            date=booking_date,
            start_time=datetime.time(14, 0),
            end_time=datetime.time(16, 0),
            description="Unauthorized Booking",
            user_id=999,
        )
    assert exc_info.value.code == "not_club_head"

    # Club not confirmed
    with pytest.raises(ConflictError) as exc_info:
        book_session(
            club=open_club,
            venue="SAC",
            date=booking_date,
            start_time=datetime.time(14, 0),
            end_time=datetime.time(16, 0),
            description="Unconfirmed Club Session",
            user_id=103,
        )
    assert exc_info.value.code == "club_not_confirmed"
