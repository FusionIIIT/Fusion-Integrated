"""
Spec tests derived from BR (Business Rules) design.
Frozen design: docs/09-gymkhana/spec-tests/BR_DESIGN.json
"""

import pytest
from datetime import datetime, time, timedelta
from decimal import Decimal
from django.test import SimpleTestCase

from modules.gymkhana.domain.policy import (
    CONFIG_ALLOWED_VENUES,
    check_cross_type_venue_conflict,
    validate_booking_time_range,
    validate_budget_amount,
    validate_club_category,
    validate_club_confirmation_transition,
    validate_club_head_authorization,
    validate_configured_venue,
    validate_event_report,
    validate_faculty_councillor,
    validate_faculty_report_review,
    validate_leadership_succession,
    validate_membership_application,
    validate_membership_approval_transition,
    validate_poll_creation,
    validate_student_leadership,
    validate_vote_eligibility,
)


class TestBRStudentLeadership(SimpleTestCase):
    """TC-BR-001: Valid Student Leadership."""

    def test_tc_br_001_p_valid_leadership(self):
        """TC-BR-001-P: Valid distinct positive student IDs accepted."""
        ok, msg = validate_student_leadership(101, 102)
        assert ok is True

    def test_tc_br_001_n1_negative_coordinator(self):
        """TC-BR-001-N1: Non-positive coordinator rejected."""
        ok, msg = validate_student_leadership(-1, 102)
        assert ok is False
        assert "Coordinator" in msg

    def test_tc_br_001_n2_same_leader(self):
        """TC-BR-001-N2: Same coordinator and co-coordinator rejected."""
        ok, msg = validate_student_leadership(101, 101)
        assert ok is False
        assert "same student" in msg.lower()

    def test_tc_br_001_n3_zero_co_coordinator(self):
        """TC-BR-001-N3: Zero co-coordinator rejected."""
        ok, msg = validate_student_leadership(101, 0)
        assert ok is False
        assert "Co-coordinator" in msg


class TestBRFacultyCouncillor(SimpleTestCase):
    """TC-BR-002: Valid Club Faculty Councillor."""

    def test_tc_br_002_p_valid(self):
        """TC-BR-002-P: Valid positive faculty ID accepted."""
        ok, msg = validate_faculty_councillor(201)
        assert ok is True

    def test_tc_br_002_n_negative(self):
        """TC-BR-002-N: Negative faculty ID rejected."""
        ok, msg = validate_faculty_councillor(-5)
        assert ok is False


class TestBRClubCategory(SimpleTestCase):
    """TC-BR-003: Allowed Club Categories."""

    def test_tc_br_003_p_technical(self):
        ok, msg = validate_club_category("Technical")
        assert ok is True

    def test_tc_br_003_p_sports(self):
        ok, msg = validate_club_category("Sports")
        assert ok is True

    def test_tc_br_003_p_cultural(self):
        ok, msg = validate_club_category("Cultural")
        assert ok is True

    def test_tc_br_003_n_invalid(self):
        ok, msg = validate_club_category("Academic")
        assert ok is False
        assert "invalid" in msg.lower()

    def test_tc_br_003_n_empty(self):
        ok, msg = validate_club_category("")
        assert ok is False


class TestBRClubConfirmation(SimpleTestCase):
    """TC-BR-004: Club Confirmation Lifecycle."""

    def test_tc_br_004_p_open_to_confirmed(self):
        ok, msg = validate_club_confirmation_transition("open")
        assert ok is True

    def test_tc_br_004_n_already_confirmed(self):
        ok, msg = validate_club_confirmation_transition("confirmed")
        assert ok is False


class TestBRBookingTimeRange(SimpleTestCase):
    """TC-BR-005: Valid Booking Time Range."""

    def test_tc_br_005_p_valid_range(self):
        ok, msg = validate_booking_time_range(time(10, 0), time(12, 0))
        assert ok is True

    def test_tc_br_005_n_start_equals_end(self):
        ok, msg = validate_booking_time_range(time(10, 0), time(10, 0))
        assert ok is False

    def test_tc_br_005_n_start_after_end(self):
        ok, msg = validate_booking_time_range(time(14, 0), time(12, 0))
        assert ok is False


class TestBRVenueConflict(SimpleTestCase):
    """TC-BR-006: Cross-Type Venue Exclusivity."""

    def test_tc_br_006_p_no_conflict(self):
        existing = [(time(8, 0), time(10, 0))]
        assert check_cross_type_venue_conflict(existing, time(10, 0), time(12, 0)) is False

    def test_tc_br_006_n_overlap(self):
        existing = [(time(10, 0), time(12, 0))]
        assert check_cross_type_venue_conflict(existing, time(11, 0), time(13, 0)) is True

    def test_tc_br_006_n_contained(self):
        existing = [(time(9, 0), time(15, 0))]
        assert check_cross_type_venue_conflict(existing, time(10, 0), time(12, 0)) is True

    def test_tc_br_006_p_empty_slots(self):
        assert check_cross_type_venue_conflict([], time(10, 0), time(12, 0)) is False


class TestBRMembershipApplication(SimpleTestCase):
    """TC-BR-007/008/009: Club Membership Rules."""

    def test_tc_br_007_p_confirmed_club(self):
        ok, msg = validate_membership_application("confirmed", False)
        assert ok is True

    def test_tc_br_007_n_unconfirmed_club(self):
        ok, msg = validate_membership_application("open", False)
        assert ok is False

    def test_tc_br_009_n_duplicate(self):
        ok, msg = validate_membership_application("confirmed", True)
        assert ok is False
        assert "duplicate" in msg.lower()


class TestBRClubHeadAuthorization(SimpleTestCase):
    """TC-BR-010: Club Head Authorization."""

    def test_tc_br_010_p_coordinator(self):
        assert validate_club_head_authorization(101, 101, 102) is True

    def test_tc_br_010_p_co_coordinator(self):
        assert validate_club_head_authorization(102, 101, 102) is True

    def test_tc_br_010_n_outsider(self):
        assert validate_club_head_authorization(999, 101, 102) is False


class TestBRMembershipApproval(SimpleTestCase):
    """TC-BR-011: Membership Approval Transition."""

    def test_tc_br_011_p_open_to_confirmed(self):
        ok, msg = validate_membership_approval_transition("open")
        assert ok is True

    def test_tc_br_011_n_already_confirmed(self):
        ok, msg = validate_membership_approval_transition("confirmed")
        assert ok is False


class TestBRPollCreation(SimpleTestCase):
    """TC-BR-012/013: Poll Creation and Targeting."""

    def test_tc_br_012_p_two_options(self):
        ok, msg = validate_poll_creation(2, "2024", "CSE")
        assert ok is True

    def test_tc_br_012_n_one_option(self):
        ok, msg = validate_poll_creation(1, "2024", "CSE")
        assert ok is False
        assert "at least 2" in msg.lower()

    def test_tc_br_013_n_blank_target(self):
        ok, msg = validate_poll_creation(3, "", "")
        assert ok is False
        assert "blank" in msg.lower()


class TestBRVoteEligibility(SimpleTestCase):
    """TC-BR-014/015: Vote Eligibility and One-Vote Rule."""

    def _future(self, days=7):
        from django.utils import timezone
        return timezone.now() + timedelta(days=days)

    def _now(self):
        from django.utils import timezone
        return timezone.now()

    def test_tc_br_014_p_eligible(self):
        ok, msg = validate_vote_eligibility(
            poll_is_active=True,
            expires_at=self._future(),
            current_time=self._now(),
            student_batch="2024",
            student_branch="CSE",
            target_batch="ALL",
            target_branch="ALL",
            already_voted=False,
        )
        assert ok is True

    def test_tc_br_014_n_expired(self):
        from django.utils import timezone
        past = timezone.now() - timedelta(days=1)
        ok, msg = validate_vote_eligibility(
            poll_is_active=True,
            expires_at=past,
            current_time=self._now(),
            student_batch="2024",
            student_branch="CSE",
            target_batch="ALL",
            target_branch="ALL",
            already_voted=False,
        )
        assert ok is False
        assert "expired" in msg.lower()

    def test_tc_br_014_n_inactive(self):
        ok, msg = validate_vote_eligibility(
            poll_is_active=False,
            expires_at=self._future(),
            current_time=self._now(),
            student_batch="2024",
            student_branch="CSE",
            target_batch="ALL",
            target_branch="ALL",
            already_voted=False,
        )
        assert ok is False
        assert "active" in msg.lower()

    def test_tc_br_014_n_batch_mismatch(self):
        ok, msg = validate_vote_eligibility(
            poll_is_active=True,
            expires_at=self._future(),
            current_time=self._now(),
            student_batch="2023",
            student_branch="CSE",
            target_batch="2024",
            target_branch="ALL",
            already_voted=False,
        )
        assert ok is False
        assert "batch" in msg.lower()

    def test_tc_br_014_n_branch_mismatch(self):
        ok, msg = validate_vote_eligibility(
            poll_is_active=True,
            expires_at=self._future(),
            current_time=self._now(),
            student_batch="2024",
            student_branch="ECE",
            target_batch="ALL",
            target_branch="CSE",
            already_voted=False,
        )
        assert ok is False
        assert "branch" in msg.lower()

    def test_tc_br_015_n_already_voted(self):
        ok, msg = validate_vote_eligibility(
            poll_is_active=True,
            expires_at=self._future(),
            current_time=self._now(),
            student_batch="2024",
            student_branch="CSE",
            target_batch="ALL",
            target_branch="ALL",
            already_voted=True,
        )
        assert ok is False
        assert "already" in msg.lower()


class TestBRLeadershipSuccession(SimpleTestCase):
    """TC-BR-016: Leadership Succession."""

    def test_tc_br_016_p_not_superseded(self):
        ok, msg = validate_leadership_succession(False)
        assert ok is True

    def test_tc_br_016_n_superseded(self):
        ok, msg = validate_leadership_succession(True)
        assert ok is False


class TestBRBudgetAmount(SimpleTestCase):
    """TC-BR-017/018: Club Budget Validation."""

    def test_tc_br_017_p_valid_amount(self):
        ok, msg = validate_budget_amount(Decimal("5000.00"), True)
        assert ok is True

    def test_tc_br_017_p_zero_amount(self):
        ok, msg = validate_budget_amount(Decimal("0.00"), True)
        assert ok is True

    def test_tc_br_017_n_negative(self):
        ok, msg = validate_budget_amount(Decimal("-100.00"), True)
        assert ok is False
        assert "negative" in msg.lower()

    def test_tc_br_018_n_no_file(self):
        ok, msg = validate_budget_amount(Decimal("1000.00"), False)
        assert ok is False
        assert "file" in msg.lower()


class TestBREventReport(SimpleTestCase):
    """TC-BR-019: Event Report File Required."""

    def test_tc_br_019_p_has_file(self):
        ok, msg = validate_event_report(True)
        assert ok is True

    def test_tc_br_019_n_no_file(self):
        ok, msg = validate_event_report(False)
        assert ok is False


class TestBRConfiguredVenue(SimpleTestCase):
    """TC-BR-020: Configured Venue Required."""

    def test_tc_br_020_p_valid_venue(self):
        ok, msg = validate_configured_venue("Student Activity Center (SAC)")
        assert ok is True

    def test_tc_br_020_n_invalid_venue(self):
        ok, msg = validate_configured_venue("Random Field")
        assert ok is False

    def test_tc_br_020_all_configured(self):
        for venue in CONFIG_ALLOWED_VENUES:
            ok, msg = validate_configured_venue(venue)
            assert ok is True, f"Venue {venue} should be valid"


class TestBRFacultyReportReview(SimpleTestCase):
    """TC-BR-021: Faculty Report Review Authorization."""

    def test_tc_br_021_p_assigned_faculty(self):
        assert validate_faculty_report_review(260, 260) is True

    def test_tc_br_021_n_unassigned_faculty(self):
        assert validate_faculty_report_review(999, 260) is False
