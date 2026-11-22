"""
Tests for Gymkhana domain policies and business rules (BR-GYM-001 to BR-GYM-021).
"""

from datetime import UTC, datetime, time
from decimal import Decimal

from modules.gymkhana.domain.policy import (
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


def test_validate_student_leadership_success():
    ok, _msg = validate_student_leadership(101, 102)
    assert ok is True


def test_validate_student_leadership_identical_leaders():
    ok, msg = validate_student_leadership(101, 101)
    assert ok is False
    assert "same student" in msg


def test_validate_student_leadership_invalid_ids():
    ok1, _ = validate_student_leadership(-1, 102)
    assert ok1 is False
    ok2, _ = validate_student_leadership(101, 0)
    assert ok2 is False


def test_validate_faculty_councillor_success():
    ok, _msg = validate_faculty_councillor(501)
    assert ok is True


def test_validate_faculty_councillor_invalid():
    ok, _msg = validate_faculty_councillor(-5)
    assert ok is False


def test_validate_club_category_allowed():
    for cat in ["Technical", "Sports", "Cultural"]:
        ok, _msg = validate_club_category(cat)
        assert ok is True


def test_validate_club_category_invalid():
    ok, msg = validate_club_category("Academic")
    assert ok is False
    assert "invalid" in msg


def test_validate_club_confirmation_transition():
    ok, _msg = validate_club_confirmation_transition("open")
    assert ok is True
    ok2, _msg2 = validate_club_confirmation_transition("confirmed")
    assert ok2 is False


def test_validate_booking_time_range():
    ok, _ = validate_booking_time_range(time(10, 0), time(11, 0))
    assert ok is True
    bad, _ = validate_booking_time_range(time(11, 0), time(10, 0))
    assert bad is False
    same, _ = validate_booking_time_range(time(10, 0), time(10, 0))
    assert same is False


def test_check_cross_type_venue_conflict():
    existing = [(time(10, 0), time(12, 0))]
    # Overlapping slot
    assert check_cross_type_venue_conflict(existing, time(11, 0), time(13, 0)) is True
    assert check_cross_type_venue_conflict(existing, time(9, 30), time(10, 30)) is True
    # Non-overlapping adjacent slots
    assert check_cross_type_venue_conflict(existing, time(8, 0), time(10, 0)) is False
    assert check_cross_type_venue_conflict(existing, time(12, 0), time(14, 0)) is False


def test_validate_membership_application():
    ok, _ = validate_membership_application("confirmed", False)
    assert ok is True
    unconf, _ = validate_membership_application("open", False)
    assert unconf is False
    dup, _ = validate_membership_application("confirmed", True)
    assert dup is False


def test_validate_club_head_authorization():
    assert validate_club_head_authorization(101, 101, 102) is True
    assert validate_club_head_authorization(102, 101, 102) is True
    assert validate_club_head_authorization(999, 101, 102) is False


def test_validate_membership_approval_transition():
    ok, _ = validate_membership_approval_transition("open")
    assert ok is True
    bad, _ = validate_membership_approval_transition("confirmed")
    assert bad is False


def test_validate_poll_creation():
    ok, _ = validate_poll_creation(2, "2024", "CSE")
    assert ok is True
    too_few, _ = validate_poll_creation(1, "2024", "CSE")
    assert too_few is False
    no_target, _ = validate_poll_creation(3, "  ", "")
    assert no_target is False


def test_validate_vote_eligibility():
    future = datetime(2099, 1, 1, tzinfo=UTC)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    # Valid vote
    ok, _ = validate_vote_eligibility(
        poll_is_active=True,
        expires_at=future,
        current_time=now,
        student_batch="2024",
        student_branch="CSE",
        target_batch="2024",
        target_branch="CSE",
        already_voted=False,
    )
    assert ok is True

    # Already voted
    dup, _ = validate_vote_eligibility(
        poll_is_active=True,
        expires_at=future,
        current_time=now,
        student_batch="2024",
        student_branch="CSE",
        target_batch="2024",
        target_branch="CSE",
        already_voted=True,
    )
    assert dup is False

    # Inactive / expired
    expired, _ = validate_vote_eligibility(
        poll_is_active=True,
        expires_at=now,
        current_time=future,
        student_batch="2024",
        student_branch="CSE",
        target_batch="2024",
        target_branch="CSE",
        already_voted=False,
    )
    assert expired is False

    # Mismatched target batch
    mismatch, _ = validate_vote_eligibility(
        poll_is_active=True,
        expires_at=future,
        current_time=now,
        student_batch="2023",
        student_branch="CSE",
        target_batch="2024",
        target_branch="CSE",
        already_voted=False,
    )
    assert mismatch is False


def test_validate_budget_amount():
    ok, _ = validate_budget_amount(Decimal("5000.00"), True)
    assert ok is True
    neg, _ = validate_budget_amount(Decimal("-10.00"), True)
    assert neg is False
    no_file, _ = validate_budget_amount(Decimal("100.00"), False)
    assert no_file is False


def test_validate_event_report():
    ok, _ = validate_event_report(True)
    assert ok is True
    no_file, _ = validate_event_report(False)
    assert no_file is False


def test_validate_configured_venue():
    ok, _ = validate_configured_venue("Student Activity Center (SAC)")
    assert ok is True
    unconf, _ = validate_configured_venue("Random Classroom 999")
    assert unconf is False


def test_validate_faculty_report_review():
    assert validate_faculty_report_review(501, 501) is True
    assert validate_faculty_report_review(502, 501) is False


def test_validate_leadership_succession():
    ok, _ = validate_leadership_succession(False)
    assert ok is True
    bad, _ = validate_leadership_succession(True)
    assert bad is False
