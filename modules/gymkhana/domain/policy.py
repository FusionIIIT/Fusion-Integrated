"""
Gymkhana Domain Policy and Business Rules.
Adheres strictly to ADR-0001 (Pure Python domain layer - zero imports of Django, DRF, or Celery).
Implements all 21 Business Rules: BR-GYM-001 through BR-GYM-021.
"""

from datetime import datetime, time
from decimal import Decimal
from enum import Enum
from typing import Sequence


# ==============================================================================
# Domain Enums & Constants
# ==============================================================================

class ClubCategory(str, Enum):
    """BR-GYM-003: Allowed Club Categories."""
    TECHNICAL = "Technical"
    SPORTS = "Sports"
    CULTURAL = "Cultural"


class ClubStatus(str, Enum):
    """BR-GYM-004: Club Confirmation Lifecycle."""
    OPEN = "open"
    CONFIRMED = "confirmed"


class MembershipStatus(str, Enum):
    """BR-GYM-011: Membership Approval Transition."""
    OPEN = "open"
    CONFIRMED = "confirmed"


class BookingType(str, Enum):
    SESSION = "session"
    EVENT = "event"


# BR-GYM-020: Configured venues for Gymkhana bookings
CONFIG_ALLOWED_VENUES: set[str] = {
    "Student Activity Center (SAC)",
    "Open Air Theatre (OAT)",
    "Main Football Ground",
    "Indoor Sports Complex",
    "L101 Lecture Hall",
    "L102 Lecture Hall",
    "Central Seminar Hall",
}


# ==============================================================================
# Business Rule Validations (BR-GYM-001 to BR-GYM-021)
# ==============================================================================

def validate_student_leadership(coordinator_id: int, co_coordinator_id: int) -> tuple[bool, str]:
    """BR-GYM-001: Valid Student Leadership.
    Club coordinator and co-coordinator must reference valid student records.
    """
    if not isinstance(coordinator_id, int) or coordinator_id <= 0:
        return False, "Coordinator must reference a valid positive student ID."
    if not isinstance(co_coordinator_id, int) or co_coordinator_id <= 0:
        return False, "Co-coordinator must reference a valid positive student ID."
    if coordinator_id == co_coordinator_id:
        return False, "Coordinator and co-coordinator cannot be the same student."
    return True, "Valid student leadership."


def validate_faculty_councillor(faculty_councillor_id: int) -> tuple[bool, str]:
    """BR-GYM-002: Valid Club Faculty Councillor.
    A Club Faculty Councillor must reference a valid faculty member.
    """
    if not isinstance(faculty_councillor_id, int) or faculty_councillor_id <= 0:
        return False, "Faculty councillor must reference a valid positive faculty ID."
    return True, "Valid faculty councillor."


def validate_club_category(category: str) -> tuple[bool, str]:
    """BR-GYM-003: Allowed Club Categories.
    Club category is limited strictly to Technical, Sports, or Cultural.
    """
    allowed = {c.value for c in ClubCategory}
    if category not in allowed:
        return False, f"Category '{category}' is invalid. Must be one of: {sorted(allowed)}."
    return True, "Valid category."


def validate_club_confirmation_transition(current_status: str) -> tuple[bool, str]:
    """BR-GYM-004: Club Confirmation Lifecycle.
    A new club is open; Student Admin approval changes an open club to confirmed.
    """
    if current_status != ClubStatus.OPEN.value:
        return False, f"Only an 'open' club can be confirmed. Current status is '{current_status}'."
    return True, "Valid transition to confirmed."


def validate_booking_time_range(start_time: time, end_time: time) -> tuple[bool, str]:
    """BR-GYM-005: Valid Booking Time Range.
    A session/event start time must be earlier than its end time.
    """
    if start_time >= end_time:
        return False, f"Start time ({start_time}) must be strictly earlier than end time ({end_time})."
    return True, "Valid booking time range."


def check_cross_type_venue_conflict(
    existing_slots: Sequence[tuple[time, time]],
    new_start: time,
    new_end: time,
) -> bool:
    """BR-GYM-006: Cross-Type Venue Exclusivity.
    No session or event may overlap any existing session or event in the same venue on the same date.
    Returns True if a conflict exists, False if the slot is clear.
    Overlap condition: (new_start < existing_end) and (new_end > existing_start).
    """
    for ex_start, ex_end in existing_slots:
        if new_start < ex_end and new_end > ex_start:
            return True
    return False


def validate_membership_application(
    club_status: str,
    has_existing_app: bool,
) -> tuple[bool, str]:
    """BR-GYM-007, BR-GYM-008, BR-GYM-009: Club Membership Rules.
    - BR-007: Membership requires confirmed club.
    - BR-008: Multiple different-club applications allowed.
    - BR-009: No duplicate same-club application.
    """
    if club_status != ClubStatus.CONFIRMED.value:
        return False, f"Cannot apply for membership: club status is '{club_status}', must be 'confirmed'."
    if has_existing_app:
        return False, "Duplicate membership application: you have already applied to this club."
    return True, "Eligible to apply for club membership."


def validate_club_head_authorization(
    actor_id: int,
    active_coordinator_id: int,
    active_co_coordinator_id: int,
) -> bool:
    """BR-GYM-010: Club Head Authorization.
    Only the applicable club coordinator or co-coordinator may perform Club Head operations.
    """
    return actor_id in (active_coordinator_id, active_co_coordinator_id)


def validate_membership_approval_transition(current_status: str) -> tuple[bool, str]:
    """BR-GYM-011: Membership Approval Transition.
    Approving an open club-membership application changes its status to confirmed.
    """
    if current_status != MembershipStatus.OPEN.value:
        return False, f"Only 'open' memberships can be approved. Current status is '{current_status}'."
    return True, "Valid membership approval transition."


def validate_poll_creation(
    num_options: int,
    target_batch: str,
    target_branch: str,
) -> tuple[bool, str]:
    """BR-GYM-012, BR-GYM-013: Poll Creation & Targeting.
    - BR-012: A voting poll must have at least two choices.
    - BR-013: Poll targeting specifies student groups by batch and branch.
    """
    if num_options < 2:
        return False, f"A voting poll must have at least 2 choices (provided: {num_options})."
    if not target_batch.strip() and not target_branch.strip():
        return False, "Target audience cannot be blank. Specify target batch and/or branch."
    return True, "Valid poll creation."


def validate_vote_eligibility(
    poll_is_active: bool,
    expires_at: datetime,
    current_time: datetime,
    student_batch: str,
    student_branch: str,
    target_batch: str,
    target_branch: str,
    already_voted: bool,
) -> tuple[bool, str]:
    """BR-GYM-014, BR-GYM-015: Active Poll Eligibility & One Vote per Student.
    - BR-014: Student may participate only in an active, unexpired poll matching target audience.
    - BR-015: One vote per student per poll.
    """
    if already_voted:
        return False, "You have already cast a vote in this poll (one vote limit)."
    if not poll_is_active:
        return False, "This poll is no longer active."
    if current_time >= expires_at:
        return False, "This poll has expired."

    # Verify audience targeting
    if target_batch.strip() and target_batch.strip() != "ALL":
        if student_batch.strip() != target_batch.strip():
            return False, f"Poll target batch '{target_batch}' does not match student batch '{student_batch}'."

    if target_branch.strip() and target_branch.strip() != "ALL":
        if student_branch.strip() != target_branch.strip():
            return False, f"Poll target branch '{target_branch}' does not match student branch '{student_branch}'."

    return True, "Eligible to vote in poll."


def validate_budget_amount(amount: Decimal | float, has_supporting_file: bool) -> tuple[bool, str]:
    """BR-GYM-017, BR-GYM-018: Club Budget Validation.
    - BR-017: Non-negative club budget (>= 0).
    - BR-018: Budget supporting file required.
    """
    if amount < Decimal("0.0"):
        return False, f"Budget amount cannot be negative ({amount})."
    if not has_supporting_file:
        return False, "A supporting file is required for submitting a club budget request."
    return True, "Valid budget request."


def validate_event_report(has_report_file: bool) -> tuple[bool, str]:
    """BR-GYM-019: Event Report File Required.
    A club event report must include its report/details file.
    """
    if not has_report_file:
        return False, "An event report documentation file is required."
    return True, "Valid event report submission."


def validate_configured_venue(venue_name: str) -> tuple[bool, str]:
    """BR-GYM-020: Configured Venue Required.
    A session/event booking must use a venue configured for Gymkhana booking.
    """
    if venue_name not in CONFIG_ALLOWED_VENUES:
        return False, f"Venue '{venue_name}' is not in configured Gymkhana venues: {sorted(CONFIG_ALLOWED_VENUES)}."
    return True, "Valid configured venue."


def validate_faculty_report_review(actor_faculty_id: int, assigned_councillor_id: int) -> bool:
    """BR-GYM-021: Faculty Report Review Authorization.
    A Club Faculty Councillor may review/access submitted reports only for the assigned club.
    """
    return actor_faculty_id == assigned_councillor_id


def validate_leadership_succession(is_superseded: bool) -> tuple[bool, str]:
    """
    BR-GYM-016: Leadership Succession.
    When club coordinator/co-coordinator assignments change, superseded active
    leadership assignments must no longer remain current.
    """
    if is_superseded:
        return False, "Superseded leadership assignments cannot remain active."
    return True, "Leadership state valid."
