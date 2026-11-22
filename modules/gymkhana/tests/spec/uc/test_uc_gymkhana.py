"""
Spec tests derived from UC (Use Case) design.
Frozen design: docs/09-gymkhana/spec-tests/UC_DESIGN.json
"""

from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from django.test import TestCase
from django.utils import timezone

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
class TestUCClubRegistration(TestCase):
    """UC-GYM-001: Register and confirm a student club."""

    def test_tc_uc_001_register_club_happy_path(self):
        """UC-GYM-001 main: Student Admin registers and confirms club."""
        club = create_club(
            name="Astronomy Club",
            category="Technical",
            coordinator_id=101,
            co_coordinator_id=102,
            faculty_councillor_id=201,
        )
        assert club.status == "open"
        confirmed = confirm_club(club_id=club.id)
        assert confirmed.status == "confirmed"

    def test_tc_uc_001_reject_duplicate_name(self):
        """UC-GYM-001 alt: Reject duplicate club name."""
        create_club(
            name="Unique Club",
            category="Sports",
            coordinator_id=103,
            co_coordinator_id=104,
            faculty_councillor_id=202,
        )
        with pytest.raises(Exception):  # noqa: B017
            create_club(
                name="Unique Club",
                category="Cultural",
                coordinator_id=105,
                co_coordinator_id=106,
                faculty_councillor_id=203,
            )

    def test_tc_uc_001_reject_double_confirmation(self):
        """UC-GYM-001 alt: Cannot confirm already-confirmed club."""
        club = create_club(
            name="Double Confirm Club",
            category="Technical",
            coordinator_id=107,
            co_coordinator_id=108,
            faculty_councillor_id=204,
        )
        confirm_club(club_id=club.id)
        with pytest.raises(ValueError):
            confirm_club(club_id=club.id)


@pytest.mark.django_db
class TestUCVenueBooking(TestCase):
    """UC-GYM-002/003: Book a venue for session or event."""

    def setUp(self):
        self.club = create_club(
            name="Venue UC Club",
            category="Sports",
            coordinator_id=140,
            co_coordinator_id=141,
            faculty_councillor_id=240,
        )

    def test_tc_uc_002_book_session(self):
        """UC-GYM-002: Book session venue successfully."""
        booking = book_venue(
            club_id=self.club.id,
            actor_id=140,
            booking_type="session",
            venue_name="Indoor Sports Complex",
            booking_date=date(2027, 5, 10),
            start_time=time(9, 0),
            end_time=time(11, 0),
        )
        assert booking.booking_type == "session"

    def test_tc_uc_003_book_event(self):
        """UC-GYM-003: Book event venue successfully."""
        booking = book_venue(
            club_id=self.club.id,
            actor_id=140,
            booking_type="event",
            venue_name="Central Seminar Hall",
            booking_date=date(2027, 5, 11),
            start_time=time(14, 0),
            end_time=time(17, 0),
            description="Annual cultural fest",
        )
        assert booking.booking_type == "event"

    def test_tc_uc_002_unauthorized_booking(self):
        """UC-GYM-002 alt: Non-coordinator cannot book."""
        with pytest.raises(PermissionError):
            book_venue(
                club_id=self.club.id,
                actor_id=999,
                booking_type="session",
                venue_name="Indoor Sports Complex",
                booking_date=date(2027, 5, 12),
                start_time=time(9, 0),
                end_time=time(11, 0),
            )


@pytest.mark.django_db
class TestUCMembership(TestCase):
    """UC-GYM-004/005: Membership application and approval."""

    def setUp(self):
        self.club = create_club(
            name="Membership UC Club",
            category="Cultural",
            coordinator_id=110,
            co_coordinator_id=111,
            faculty_councillor_id=210,
        )
        confirm_club(club_id=self.club.id)

    def test_tc_uc_004_apply_membership(self):
        """UC-GYM-004: Student applies for membership."""
        m = apply_club_membership(club_id=self.club.id, student_id=301)
        assert m.status == "open"

    def test_tc_uc_005_approve_membership(self):
        """UC-GYM-005: Club head approves membership."""
        m = apply_club_membership(club_id=self.club.id, student_id=302)
        approved = approve_club_membership(
            membership_id=m.id, actor_id=110
        )
        assert approved.status == "confirmed"

    def test_tc_uc_005_unauthorized_approval(self):
        """UC-GYM-005 alt: Non-coordinator cannot approve."""
        m = apply_club_membership(club_id=self.club.id, student_id=303)
        with pytest.raises(PermissionError):
            approve_club_membership(membership_id=m.id, actor_id=999)


@pytest.mark.django_db
class TestUCPolling(TestCase):
    """UC-GYM-006/007: Create poll and cast vote."""

    def setUp(self):
        self.club = create_club(
            name="Polling UC Club",
            category="Technical",
            coordinator_id=150,
            co_coordinator_id=151,
            faculty_councillor_id=250,
        )

    def test_tc_uc_006_create_poll(self):
        """UC-GYM-006: Coordinator creates voting poll."""
        poll = create_voting_poll(
            club_id=self.club.id,
            actor_id=150,
            title="Best Editor",
            options=["VS Code", "Neovim"],
            expires_at=timezone.now() + timedelta(days=3),
            target_batch="ALL",
            target_branch="ALL",
        )
        assert poll.options.count() == 2

    def test_tc_uc_007_cast_vote(self):
        """UC-GYM-007: Eligible student casts vote."""
        poll = create_voting_poll(
            club_id=self.club.id,
            actor_id=150,
            title="Best OS",
            options=["Linux", "macOS"],
            expires_at=timezone.now() + timedelta(days=3),
            target_batch="ALL",
            target_branch="ALL",
        )
        opt = poll.options.first()
        vote = cast_poll_vote(
            poll_id=poll.id,
            option_id=opt.id,
            student_id=501,
            student_batch="2024",
            student_branch="CSE",
        )
        assert vote.student_id == 501


@pytest.mark.django_db
class TestUCLeadershipChange(TestCase):
    """UC-GYM-008: Change club leadership."""

    def setUp(self):
        self.club = create_club(
            name="Leadership UC Club",
            category="Technical",
            coordinator_id=101,
            co_coordinator_id=102,
            faculty_councillor_id=201,
        )

    def test_tc_uc_008_change_leadership(self):
        """UC-GYM-008: Authorized head changes coordinators."""
        new = change_club_leadership(
            club_id=self.club.id,
            actor_id=101,
            new_coordinator_id=103,
            new_co_coordinator_id=104,
        )
        assert new.is_active is True
        assert new.coordinator_id == 103

    def test_tc_uc_008_unauthorized_change(self):
        """UC-GYM-008 alt: Non-coordinator cannot change leadership."""
        with pytest.raises(PermissionError):
            change_club_leadership(
                club_id=self.club.id,
                actor_id=999,
                new_coordinator_id=103,
                new_co_coordinator_id=104,
            )


@pytest.mark.django_db
class TestUCBudgetAndReports(TestCase):
    """UC-GYM-009/010/012: Budget, event report, faculty review."""

    def setUp(self):
        self.club = create_club(
            name="Budget UC Club",
            category="Technical",
            coordinator_id=160,
            co_coordinator_id=161,
            faculty_councillor_id=260,
        )

    def test_tc_uc_009_submit_budget(self):
        """UC-GYM-009: Submit budget request."""
        req = submit_budget_request(
            club_id=self.club.id,
            actor_id=160,
            requested_amount=Decimal("2500.00"),
            description="Club jerseys",
            supporting_file="jerseys.pdf",
        )
        assert req.status == "open"

    def test_tc_uc_010_submit_event_report(self):
        """UC-GYM-010: Submit event report."""
        report = submit_event_report(
            club_id=self.club.id,
            actor_id=160,
            event_name="Workshop",
            event_date=date(2027, 6, 1),
            report_file="workshop.pdf",
        )
        assert report.event_name == "Workshop"

    def test_tc_uc_012_faculty_review_report(self):
        """UC-GYM-012: Faculty councillor reviews event report."""
        report = submit_event_report(
            club_id=self.club.id,
            actor_id=160,
            event_name="Hackathon",
            event_date=date(2027, 6, 15),
            report_file="hackathon.pdf",
        )
        reviewed = review_event_report(
            report_id=report.id, faculty_id=260
        )
        assert reviewed.id == report.id

    def test_tc_uc_012_unauthorized_faculty_review(self):
        """UC-GYM-012 alt: Non-assigned faculty cannot review."""
        report = submit_event_report(
            club_id=self.club.id,
            actor_id=160,
            event_name="Seminar",
            event_date=date(2027, 7, 1),
            report_file="seminar.pdf",
        )
        with pytest.raises(PermissionError):
            review_event_report(report_id=report.id, faculty_id=999)
