"""
Spec tests derived from WF (Workflow / Business Workflow) design.
Frozen design: docs/09-gymkhana/spec-tests/WF_DESIGN.json
"""

import pytest
from decimal import Decimal
from datetime import date, time, timedelta
from django.test import TestCase
from django.utils import timezone

from modules.gymkhana.models import (
    Club,
    ClubLeadership,
    ClubMembership,
    PollVote,
    VotingPoll,
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
class TestWFClubLifecycle(TestCase):
    """BW-GYM-03: Club Registration and Confirmation Workflow."""

    def test_tc_wf_001_full_club_lifecycle(self):
        """BW-GYM-03: Create club -> confirm -> change leadership."""
        club = create_club(
            name="Lifecycle Club",
            category="Technical",
            coordinator_id=101,
            co_coordinator_id=102,
            faculty_councillor_id=201,
        )
        assert club.status == "open"

        confirmed = confirm_club(club_id=club.id)
        assert confirmed.status == "confirmed"

        new_lead = change_club_leadership(
            club_id=club.id,
            actor_id=101,
            new_coordinator_id=103,
            new_co_coordinator_id=104,
        )
        assert new_lead.is_active is True
        assert new_lead.coordinator_id == 103

        old_leads = ClubLeadership.objects.filter(
            club=club, coordinator_id=101
        )
        assert all(not lead.is_active for lead in old_leads)


@pytest.mark.django_db
class TestWFMembershipWorkflow(TestCase):
    """BW-GYM-01: Membership Application and Approval Workflow."""

    def setUp(self):
        self.club = create_club(
            name="Membership WF Club",
            category="Cultural",
            coordinator_id=110,
            co_coordinator_id=111,
            faculty_councillor_id=210,
        )
        confirm_club(club_id=self.club.id)

    def test_tc_wf_002_membership_happy_path(self):
        """BW-GYM-01: Apply -> approve membership workflow."""
        m = apply_club_membership(club_id=self.club.id, student_id=301)
        assert m.status == "open"

        approved = approve_club_membership(
            membership_id=m.id, actor_id=110
        )
        assert approved.status == "confirmed"
        assert approved.confirmed_at is not None

    def test_tc_wf_002_reject_unconfirmed_then_confirm(self):
        """BW-GYM-01 alt: Cannot apply until club is confirmed."""
        new_club = create_club(
            name="Pending WF Club",
            category="Sports",
            coordinator_id=120,
            co_coordinator_id=121,
            faculty_councillor_id=220,
        )
        with pytest.raises(ValueError):
            apply_club_membership(club_id=new_club.id, student_id=302)

        confirm_club(club_id=new_club.id)
        m = apply_club_membership(club_id=new_club.id, student_id=302)
        assert m.status == "open"


@pytest.mark.django_db
class TestWFVotingWorkflow(TestCase):
    """BW-GYM-02: Voting Poll Lifecycle Workflow."""

    def setUp(self):
        self.club = create_club(
            name="Voting WF Club",
            category="Technical",
            coordinator_id=150,
            co_coordinator_id=151,
            faculty_councillor_id=250,
        )

    def test_tc_wf_003_poll_create_vote_workflow(self):
        """BW-GYM-02: Create poll -> cast votes -> verify counts."""
        poll = create_voting_poll(
            club_id=self.club.id,
            actor_id=150,
            title="Best Language WF",
            options=["Python", "Rust", "Go"],
            expires_at=timezone.now() + timedelta(days=7),
            target_batch="ALL",
            target_branch="ALL",
        )
        assert poll.is_active is True
        assert poll.options.count() == 3

        opt_a = poll.options.all()[0]
        opt_b = poll.options.all()[1]

        cast_poll_vote(
            poll_id=poll.id,
            option_id=opt_a.id,
            student_id=501,
            student_batch="2024",
            student_branch="CSE",
        )
        cast_poll_vote(
            poll_id=poll.id,
            option_id=opt_b.id,
            student_id=502,
            student_batch="2024",
            student_branch="ECE",
        )
        cast_poll_vote(
            poll_id=poll.id,
            option_id=opt_a.id,
            student_id=503,
            student_batch="2024",
            student_branch="CSE",
        )

        total_votes = PollVote.objects.filter(poll=poll).count()
        assert total_votes == 3

        opt_a_votes = PollVote.objects.filter(poll=poll, option=opt_a).count()
        assert opt_a_votes == 2

    def test_tc_wf_003_reject_duplicate_vote_in_workflow(self):
        """BW-GYM-02 alt: Second vote by same student rejected."""
        poll = create_voting_poll(
            club_id=self.club.id,
            actor_id=150,
            title="Dup WF Poll",
            options=["X", "Y"],
            expires_at=timezone.now() + timedelta(days=7),
            target_batch="ALL",
            target_branch="ALL",
        )
        opt = poll.options.first()
        cast_poll_vote(
            poll_id=poll.id,
            option_id=opt.id,
            student_id=504,
            student_batch="2024",
            student_branch="CSE",
        )
        with pytest.raises((ValueError, Exception)):
            cast_poll_vote(
                poll_id=poll.id,
                option_id=opt.id,
                student_id=504,
                student_batch="2024",
                student_branch="CSE",
            )


@pytest.mark.django_db
class TestWFBudgetAndReportWorkflow(TestCase):
    """BW-GYM-04/05: Budget and Event Report Workflow."""

    def setUp(self):
        self.club = create_club(
            name="Budget WF Club",
            category="Technical",
            coordinator_id=160,
            co_coordinator_id=161,
            faculty_councillor_id=260,
        )

    def test_tc_wf_004_budget_submission_workflow(self):
        """BW-GYM-04: Submit budget -> verify record."""
        req = submit_budget_request(
            club_id=self.club.id,
            actor_id=160,
            requested_amount=Decimal("7500.00"),
            description="Equipment and travel",
            supporting_file="budget_v2.pdf",
        )
        assert req.status == "open"
        assert req.requested_amount == Decimal("7500.00")
        assert req.supporting_file == "budget_v2.pdf"

    def test_tc_wf_005_event_report_and_review(self):
        """BW-GYM-05: Submit report -> faculty review workflow."""
        report = submit_event_report(
            club_id=self.club.id,
            actor_id=160,
            event_name="Tech Talk WF",
            event_date=date(2027, 8, 20),
            report_file="techtalk.pdf",
        )
        assert report.event_name == "Tech Talk WF"

        reviewed = review_event_report(
            report_id=report.id, faculty_id=260
        )
        assert reviewed.id == report.id

    def test_tc_wf_005_unauthorized_review(self):
        """BW-GYM-05 alt: Non-assigned faculty cannot review."""
        report = submit_event_report(
            club_id=self.club.id,
            actor_id=160,
            event_name="Seminar WF",
            event_date=date(2027, 9, 1),
            report_file="seminar.pdf",
        )
        with pytest.raises(PermissionError):
            review_event_report(report_id=report.id, faculty_id=999)


@pytest.mark.django_db
class TestWFVenueBookingWorkflow(TestCase):
    """BW-GYM-06: Venue Booking Workflow."""

    def setUp(self):
        self.club = create_club(
            name="Venue WF Club",
            category="Sports",
            coordinator_id=140,
            co_coordinator_id=141,
            faculty_councillor_id=240,
        )

    def test_tc_wf_006_book_multiple_venues(self):
        """BW-GYM-06: Book multiple non-conflicting venues."""
        b1 = book_venue(
            club_id=self.club.id,
            actor_id=140,
            booking_type="session",
            venue_name="Indoor Sports Complex",
            booking_date=date(2027, 10, 1),
            start_time=time(9, 0),
            end_time=time(11, 0),
        )
        b2 = book_venue(
            club_id=self.club.id,
            actor_id=140,
            booking_type="event",
            venue_name="Open Air Theatre (OAT)",
            booking_date=date(2027, 10, 1),
            start_time=time(14, 0),
            end_time=time(17, 0),
        )
        assert b1.venue_name != b2.venue_name

    def test_tc_wf_006_conflict_detection(self):
        """BW-GYM-06 alt: Conflict detected for overlapping booking."""
        book_venue(
            club_id=self.club.id,
            actor_id=140,
            booking_type="session",
            venue_name="Main Football Ground",
            booking_date=date(2027, 10, 5),
            start_time=time(8, 0),
            end_time=time(10, 0),
        )
        with pytest.raises(ValueError):
            book_venue(
                club_id=self.club.id,
                actor_id=140,
                booking_type="event",
                venue_name="Main Football Ground",
                booking_date=date(2027, 10, 5),
                start_time=time(9, 0),
                end_time=time(11, 0),
            )
