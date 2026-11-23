"""Model constraints and database integrity tests for Gymkhana."""

import datetime
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from modules.gymkhana.models.booking import VenueBooking
from modules.gymkhana.models.budget import ClubBudgetRequest
from modules.gymkhana.models.club import Club
from modules.gymkhana.models.membership import ClubMembership
from modules.gymkhana.models.poll import (
    Poll,
    PollChoice,
    PollVote,
)

pytestmark = pytest.mark.django_db


def test_club_constraints():
    # Valid club
    club = Club.objects.create(
        name="Coding Club",
        category="technical",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
        status="open",
    )
    assert club.pk is not None

    # Invalid category check constraint
    with pytest.raises(IntegrityError), transaction.atomic():
        Club.objects.create(
            name="Invalid Club",
            category="finance",
            coordinator_id=103,
            co_coordinator_id=104,
            faculty_councillor_id=201,
        )

    # Identical coordinator & co-coordinator check constraint
    with pytest.raises(IntegrityError), transaction.atomic():
        Club.objects.create(
            name="Mirror Club",
            category="cultural",
            coordinator_id=105,
            co_coordinator_id=105,
            faculty_councillor_id=201,
        )


def test_booking_constraints():
    club = Club.objects.create(
        name="Robotics Club",
        category="technical",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
        status="confirmed",
    )

    # Valid booking
    b = VenueBooking.objects.create(
        club=club,
        booking_type="session",
        venue="Hall 1",
        booking_date=datetime.date(2026, 12, 1),
        start_time=datetime.time(10, 0),
        end_time=datetime.time(11, 0),
        booked_by_id=101,
    )
    assert b.pk is not None

    # Check constraint start_time < end_time
    with pytest.raises(IntegrityError), transaction.atomic():
        VenueBooking.objects.create(
            club=club,
            booking_type="session",
            venue="Hall 1",
            booking_date=datetime.date(2026, 12, 1),
            start_time=datetime.time(12, 0),
            end_time=datetime.time(11, 0),
            booked_by_id=101,
        )


def test_membership_unique_constraint():
    club = Club.objects.create(
        name="Dance Club",
        category="cultural",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
        status="confirmed",
    )
    ClubMembership.objects.create(club=club, student_id=301, status="open")

    # Duplicate membership for same student and club (BR-GYM-009)
    with pytest.raises(IntegrityError), transaction.atomic():
        ClubMembership.objects.create(club=club, student_id=301, status="open")


def test_poll_vote_unique_constraint():
    club = Club.objects.create(
        name="Sports Club",
        category="sports",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
        status="confirmed",
    )
    poll = Poll.objects.create(
        club=club,
        created_by_id=101,
        title="Tournament Format",
        expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=2),
    )
    c1 = PollChoice.objects.create(poll=poll, choice_text="Knockout")
    c2 = PollChoice.objects.create(poll=poll, choice_text="Round Robin")

    PollVote.objects.create(poll=poll, student_id=401, choice=c1)

    # Second vote in same poll by same student (BR-GYM-015)
    with pytest.raises(IntegrityError), transaction.atomic():
        PollVote.objects.create(poll=poll, student_id=401, choice=c2)


def test_budget_amount_check_constraint():
    club = Club.objects.create(
        name="Music Club",
        category="cultural",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
        status="confirmed",
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        ClubBudgetRequest.objects.create(
            club=club,
            submitted_by_id=101,
            amount=Decimal("-10.00"),
            purpose="Guitars",
            supporting_file="test.pdf",
        )
