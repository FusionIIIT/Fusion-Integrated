"""
Tests for Gymkhana application workflows and services (UC-GYM-001 to UC-GYM-012, BW-GYM-01 to BW-GYM-03).
"""

from datetime import UTC, date, datetime, time
from decimal import Decimal

import pytest

from modules.gymkhana.models import (
    ClubLeadership,
)
from modules.gymkhana.services.applications import (
    apply_club_membership,
    approve_club_membership,
    book_venue,
    cast_poll_vote,
    change_club_leadership,
    confirm_club,
    create_club,
    create_voting_poll,
    review_event_report,
    submit_budget_request,
    submit_event_report,
)


@pytest.mark.django_db
def test_create_and_confirm_club():
    club = create_club(
        name="Robotics Society",
        category="Technical",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=501,
        description="Technical Robotics Club",
    )
    assert club.id is not None
    assert club.status == "open"
    leadership = ClubLeadership.objects.get(club=club, is_active=True)
    assert leadership.coordinator_id == 101

    confirmed = confirm_club(club_id=club.id)
    assert confirmed.status == "confirmed"

    # Confirming already confirmed club raises error
    with pytest.raises(ValueError):
        confirm_club(club_id=club.id)


@pytest.mark.django_db
def test_change_club_leadership_workflow():
    club = create_club(
        name="Music Club",
        category="Cultural",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=501,
    )
    # Non-coordinator cannot change leadership
    with pytest.raises(PermissionError):
        change_club_leadership(
            club_id=club.id,
            actor_id=999,
            new_coordinator_id=103,
            new_co_coordinator_id=104,
        )

    new_lead = change_club_leadership(
        club_id=club.id,
        actor_id=101,
        new_coordinator_id=103,
        new_co_coordinator_id=104,
    )
    assert new_lead.is_active is True
    assert new_lead.coordinator_id == 103

    # Check previous leadership was deactivated
    old_lead = ClubLeadership.objects.get(club=club, coordinator_id=101)
    assert old_lead.is_active is False


@pytest.mark.django_db
def test_book_venue_workflow():
    club = create_club(
        name="Football Club",
        category="Sports",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=501,
    )
    booking_date = date(2026, 12, 1)

    # Valid session booking
    booking1 = book_venue(
        club_id=club.id,
        actor_id=101,
        booking_type="session",
        venue_name="Main Football Ground",
        booking_date=booking_date,
        start_time=time(16, 0),
        end_time=time(18, 0),
        description="Evening practice",
    )
    assert booking1.id is not None

    # Conflicting booking on same venue and overlapping time
    with pytest.raises(ValueError, match="already booked"):
        book_venue(
            club_id=club.id,
            actor_id=102,
            booking_type="event",
            venue_name="Main Football Ground",
            booking_date=booking_date,
            start_time=time(17, 0),
            end_time=time(19, 0),
            description="Match",
        )


@pytest.mark.django_db
def test_membership_application_and_approval():
    club = create_club(
        name="Coding Club",
        category="Technical",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=501,
    )
    # Cannot apply to open club
    with pytest.raises(ValueError, match="must be 'confirmed'"):
        apply_club_membership(club_id=club.id, student_id=201)

    confirm_club(club_id=club.id)
    membership = apply_club_membership(club_id=club.id, student_id=201)
    assert membership.status == "open"
    assert membership.confirmed_at is None

    # Cannot apply twice
    with pytest.raises(ValueError, match="Duplicate membership"):
        apply_club_membership(club_id=club.id, student_id=201)

    # Unauthorized approval rejected
    with pytest.raises(PermissionError):
        approve_club_membership(membership_id=membership.id, actor_id=999)

    # Authorized approval by coordinator
    approved = approve_club_membership(membership_id=membership.id, actor_id=101)
    assert approved.status == "confirmed"
    assert approved.confirmed_at is not None


@pytest.mark.django_db
def test_voting_poll_and_cast_vote():
    club = create_club(
        name="Debate Club",
        category="Cultural",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=501,
    )
    future = datetime(2099, 1, 1, tzinfo=UTC)
    poll = create_voting_poll(
        club_id=club.id,
        actor_id=101,
        title="Club Mascot Election",
        options=["Eagle", "Lion"],
        expires_at=future,
        target_batch="2024",
        target_branch="CSE",
    )
    assert poll.id is not None
    assert poll.options.count() == 2

    option = poll.options.first()
    vote = cast_poll_vote(
        poll_id=poll.id,
        student_id=201,
        option_id=option.id,
        student_batch="2024",
        student_branch="CSE",
    )
    assert vote.id is not None

    # Second vote rejected
    with pytest.raises(ValueError, match="already cast a vote"):
        cast_poll_vote(
            poll_id=poll.id,
            student_id=201,
            option_id=option.id,
            student_batch="2024",
            student_branch="CSE",
        )


@pytest.mark.django_db
def test_budget_request_and_event_reports():
    club = create_club(
        name="Drama Society",
        category="Cultural",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=501,
    )
    budget = submit_budget_request(
        club_id=club.id,
        actor_id=101,
        requested_amount=Decimal("15000.00"),
        description="Annual stage play production",
        supporting_file="budget_breakdown.pdf",
    )
    assert budget.id is not None
    assert budget.status == "open"

    report = submit_event_report(
        club_id=club.id,
        actor_id=101,
        event_name="Street Play Showcase",
        event_date=date(2026, 11, 20),
        report_file="street_play_report.pdf",
    )
    assert report.id is not None

    # Review event report by faculty councillor
    reviewed = review_event_report(report_id=report.id, faculty_id=501)
    assert reviewed.id == report.id

    # Review by unauthorized faculty rejected
    with pytest.raises(PermissionError):
        review_event_report(report_id=report.id, faculty_id=502)
