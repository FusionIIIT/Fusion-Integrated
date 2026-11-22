"""
Spec tests derived from FR (Functional Requirements / CFR+AFR) design.
Frozen design: docs/09-gymkhana/spec-tests/FR_DESIGN.json
"""

import pytest
from decimal import Decimal
from datetime import date, time, timedelta
from django.test import TestCase
from django.utils import timezone

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
    submit_budget_request,
    submit_event_report,
)


@pytest.mark.django_db
class TestFRClubCreation(TestCase):
    """TC-FR-001 through TC-FR-005: Club creation functional requirements."""

    def test_tc_fr_001_create_club_valid(self):
        """TC-FR-001: Student Admin creates club with required fields."""
        club = create_club(
            name="Robotics Club",
            category="Technical",
            coordinator_id=101,
            co_coordinator_id=102,
            faculty_councillor_id=201,
            description="Technical robotics club",
        )
        assert club.status == "open"
        assert club.name == "Robotics Club"
        leadership = ClubLeadership.objects.filter(club=club, is_active=True).first()
        assert leadership is not None
        assert leadership.coordinator_id == 101

    def test_tc_fr_002_reject_invalid_coordinator(self):
        """TC-FR-002: Reject club creation with invalid coordinator."""
        with pytest.raises(ValueError):
            create_club(
                name="Bad Club",
                category="Technical",
                coordinator_id=-1,
                co_coordinator_id=102,
                faculty_councillor_id=201,
            )

    def test_tc_fr_003_reject_invalid_faculty(self):
        """TC-FR-003: Reject club creation with invalid faculty councillor."""
        with pytest.raises(ValueError):
            create_club(
                name="Bad Faculty Club",
                category="Technical",
                coordinator_id=101,
                co_coordinator_id=102,
                faculty_councillor_id=-5,
            )

    def test_tc_fr_004_reject_invalid_category(self):
        """TC-FR-004: Category restricted to Technical/Sports/Cultural."""
        with pytest.raises(ValueError):
            create_club(
                name="Academic Club",
                category="Academic",
                coordinator_id=101,
                co_coordinator_id=102,
                faculty_councillor_id=201,
            )

    def test_tc_fr_005_initial_status_open(self):
        """TC-FR-005: Newly created club has status 'open'."""
        club = create_club(
            name="Dance Club",
            category="Cultural",
            coordinator_id=103,
            co_coordinator_id=104,
            faculty_councillor_id=202,
        )
        assert club.status == "open"


@pytest.mark.django_db
class TestFRClubApproval(TestCase):
    """TC-FR-006: Club confirmation lifecycle."""

    def test_tc_fr_006_confirm_open_club(self):
        """TC-FR-006: Student Admin confirms an open club."""
        club = create_club(
            name="Chess Club",
            category="Sports",
            coordinator_id=105,
            co_coordinator_id=106,
            faculty_councillor_id=203,
        )
        confirmed = confirm_club(club_id=club.id)
        assert confirmed.status == "confirmed"


@pytest.mark.django_db
class TestFRLeadership(TestCase):
    """TC-FR-007 through TC-FR-009: Leadership management."""

    def setUp(self):
        self.club = create_club(
            name="Coding Club",
            category="Technical",
            coordinator_id=101,
            co_coordinator_id=102,
            faculty_councillor_id=201,
        )

    def test_tc_fr_007_change_leadership(self):
        """TC-FR-007: Authorized Club Head changes coordinators."""
        new_lead = change_club_leadership(
            club_id=self.club.id,
            actor_id=101,
            new_coordinator_id=103,
            new_co_coordinator_id=104,
        )
        assert new_lead.coordinator_id == 103
        assert new_lead.co_coordinator_id == 104
        assert new_lead.is_active is True

    def test_tc_fr_008_reject_invalid_new_leader(self):
        """TC-FR-008: Reject invalid new leader IDs."""
        with pytest.raises(ValueError):
            change_club_leadership(
                club_id=self.club.id,
                actor_id=101,
                new_coordinator_id=-1,
                new_co_coordinator_id=104,
            )

    def test_tc_fr_009_supersede_old_leadership(self):
        """TC-FR-009: Superseded leadership is deactivated."""
        change_club_leadership(
            club_id=self.club.id,
            actor_id=101,
            new_coordinator_id=103,
            new_co_coordinator_id=104,
        )
        old = ClubLeadership.objects.filter(
            club=self.club, coordinator_id=101
        ).first()
        assert old.is_active is False


@pytest.mark.django_db
class TestFRMembership(TestCase):
    """TC-FR-010 through TC-FR-014: Membership functional requirements."""

    def setUp(self):
        self.club = create_club(
            name="Music Club",
            category="Cultural",
            coordinator_id=110,
            co_coordinator_id=111,
            faculty_councillor_id=210,
        )
        confirm_club(club_id=self.club.id)

    def test_tc_fr_010_apply_membership(self):
        """TC-FR-010: Student applies for membership to confirmed club."""
        membership = apply_club_membership(
            club_id=self.club.id, student_id=301
        )
        assert membership.status == "open"
        assert membership.student_id == 301

    def test_tc_fr_011_reject_unconfirmed_club(self):
        """TC-FR-011: Reject membership for unconfirmed club."""
        open_club = create_club(
            name="Unconfirmed Club",
            category="Technical",
            coordinator_id=120,
            co_coordinator_id=121,
            faculty_councillor_id=220,
        )
        with pytest.raises(ValueError):
            apply_club_membership(
                club_id=open_club.id, student_id=302
            )

    def test_tc_fr_012_reject_duplicate_membership(self):
        """TC-FR-012: Reject duplicate same-club application."""
        apply_club_membership(club_id=self.club.id, student_id=303)
        with pytest.raises((ValueError, Exception)):
            apply_club_membership(
                club_id=self.club.id, student_id=303
            )

    def test_tc_fr_013_approve_membership(self):
        """TC-FR-013: Club head approves open membership."""
        membership = apply_club_membership(
            club_id=self.club.id, student_id=304
        )
        approved = approve_club_membership(
            membership_id=membership.id, actor_id=110
        )
        assert approved.status == "confirmed"

    def test_tc_fr_014_multiple_clubs(self):
        """TC-FR-014: Student may apply to multiple different clubs."""
        club2 = create_club(
            name="Drama Club",
            category="Cultural",
            coordinator_id=130,
            co_coordinator_id=131,
            faculty_councillor_id=230,
        )
        confirm_club(club_id=club2.id)
        m1 = apply_club_membership(
            club_id=self.club.id, student_id=305
        )
        m2 = apply_club_membership(
            club_id=club2.id, student_id=305
        )
        assert m1.club_id != m2.club_id
        assert m1.student_id == m2.student_id


@pytest.mark.django_db
class TestFRVenueBooking(TestCase):
    """TC-FR-015 through TC-FR-018: Venue booking functional requirements."""

    def setUp(self):
        self.club = create_club(
            name="Sports Club",
            category="Sports",
            coordinator_id=140,
            co_coordinator_id=141,
            faculty_councillor_id=240,
        )

    def test_tc_fr_015_book_venue_valid(self):
        """TC-FR-015: Book venue with valid time range."""
        booking = book_venue(
            club_id=self.club.id,
            actor_id=140,
            booking_type="session",
            venue_name="Student Activity Center (SAC)",
            booking_date=date(2027, 3, 15),
            start_time=time(10, 0),
            end_time=time(12, 0),
            description="Weekly practice session",
        )
        assert booking.venue_name == "Student Activity Center (SAC)"

    def test_tc_fr_016_reject_invalid_time_range(self):
        """TC-FR-016: Reject booking where start >= end."""
        with pytest.raises(ValueError):
            book_venue(
                club_id=self.club.id,
                actor_id=140,
                booking_type="session",
                venue_name="Student Activity Center (SAC)",
                booking_date=date(2027, 3, 16),
                start_time=time(14, 0),
                end_time=time(12, 0),
            )

    def test_tc_fr_017_reject_unconfigured_venue(self):
        """TC-FR-017: Reject booking at unconfigured venue."""
        with pytest.raises(ValueError):
            book_venue(
                club_id=self.club.id,
                actor_id=140,
                booking_type="event",
                venue_name="Unknown Hall",
                booking_date=date(2027, 3, 17),
                start_time=time(10, 0),
                end_time=time(12, 0),
            )

    def test_tc_fr_018_reject_overlapping_booking(self):
        """TC-FR-018: Reject overlapping venue booking."""
        book_venue(
            club_id=self.club.id,
            actor_id=140,
            booking_type="session",
            venue_name="Open Air Theatre (OAT)",
            booking_date=date(2027, 4, 1),
            start_time=time(10, 0),
            end_time=time(12, 0),
        )
        with pytest.raises(ValueError):
            book_venue(
                club_id=self.club.id,
                actor_id=140,
                booking_type="event",
                venue_name="Open Air Theatre (OAT)",
                booking_date=date(2027, 4, 1),
                start_time=time(11, 0),
                end_time=time(13, 0),
            )


@pytest.mark.django_db
class TestFRPolling(TestCase):
    """TC-FR-019 through TC-FR-022: Voting poll functional requirements."""

    def setUp(self):
        self.club = create_club(
            name="Poll Test Club",
            category="Technical",
            coordinator_id=150,
            co_coordinator_id=151,
            faculty_councillor_id=250,
        )

    def test_tc_fr_019_create_poll(self):
        """TC-FR-019: Create poll with >=2 options."""
        poll = create_voting_poll(
            club_id=self.club.id,
            actor_id=150,
            title="Best Language",
            description="Choose your favourite",
            target_batch="2024",
            target_branch="CSE",
            expires_at=timezone.now() + timedelta(days=7),
            options=["Python", "Rust", "Go"],
        )
        assert poll.is_active is True
        assert poll.options.count() == 3

    def test_tc_fr_020_reject_single_option_poll(self):
        """TC-FR-020: Reject poll with fewer than 2 options."""
        with pytest.raises(ValueError):
            create_voting_poll(
                club_id=self.club.id,
                actor_id=150,
                title="Bad Poll",
                description="Only one option",
                target_batch="2024",
                target_branch="CSE",
                expires_at=timezone.now() + timedelta(days=7),
                options=["Only Option"],
            )

    def test_tc_fr_021_cast_vote(self):
        """TC-FR-021: Eligible student casts a vote."""
        poll = create_voting_poll(
            club_id=self.club.id,
            actor_id=150,
            title="Framework Poll",
            description="Best framework",
            target_batch="ALL",
            target_branch="ALL",
            expires_at=timezone.now() + timedelta(days=7),
            options=["Django", "Flask"],
        )
        option = poll.options.first()
        vote = cast_poll_vote(
            poll_id=poll.id,
            option_id=option.id,
            student_id=501,
            student_batch="2024",
            student_branch="CSE",
        )
        assert vote.student_id == 501

    def test_tc_fr_022_reject_duplicate_vote(self):
        """TC-FR-022: Reject second vote in same poll."""
        poll = create_voting_poll(
            club_id=self.club.id,
            actor_id=150,
            title="Dup Vote Poll",
            description="Test",
            target_batch="ALL",
            target_branch="ALL",
            expires_at=timezone.now() + timedelta(days=7),
            options=["A", "B"],
        )
        option = poll.options.first()
        cast_poll_vote(
            poll_id=poll.id,
            option_id=option.id,
            student_id=502,
            student_batch="2024",
            student_branch="CSE",
        )
        with pytest.raises((ValueError, Exception)):
            cast_poll_vote(
                poll_id=poll.id,
                option_id=option.id,
                student_id=502,
                student_batch="2024",
                student_branch="CSE",
            )


@pytest.mark.django_db
class TestFRBudgetAndReports(TestCase):
    """TC-FR-023 through TC-FR-026: Budget and event report requirements."""

    def setUp(self):
        self.club = create_club(
            name="Budget Test Club",
            category="Technical",
            coordinator_id=160,
            co_coordinator_id=161,
            faculty_councillor_id=260,
        )

    def test_tc_fr_023_submit_budget_request(self):
        """TC-FR-023: Submit valid budget request."""
        req = submit_budget_request(
            club_id=self.club.id,
            actor_id=160,
            requested_amount=Decimal("5000.00"),
            description="Equipment purchase",
            supporting_file="budget_plan.pdf",
        )
        assert req.requested_amount == Decimal("5000.00")

    def test_tc_fr_024_reject_negative_budget(self):
        """TC-FR-024: Reject negative budget amount."""
        with pytest.raises(ValueError):
            submit_budget_request(
                club_id=self.club.id,
                actor_id=160,
                requested_amount=Decimal("-100.00"),
                description="Invalid budget",
                supporting_file="budget.pdf",
            )

    def test_tc_fr_025_reject_budget_without_file(self):
        """TC-FR-025: Reject budget without supporting file."""
        with pytest.raises(ValueError):
            submit_budget_request(
                club_id=self.club.id,
                actor_id=160,
                requested_amount=Decimal("1000.00"),
                description="No file budget",
                supporting_file="",
            )

    def test_tc_fr_026_submit_event_report(self):
        """TC-FR-026: Submit event report with required file."""
        report = submit_event_report(
            club_id=self.club.id,
            actor_id=160,
            event_name="Annual Tech Fest",
            event_date=date(2027, 2, 15),
            report_file="techfest_report.pdf",
        )
        assert report.event_name == "Annual Tech Fest"
