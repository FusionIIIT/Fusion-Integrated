"""Pure-Python domain tests for Gymkhana (no database, runs in milliseconds)."""
import datetime

import pytest

from modules.gymkhana.domain.exceptions import (
    ActorNotAllowed,
    GuardFailed,
    InvalidPollChoicesError,
    InvalidTimeRangeError,
    InvalidTransition,
    InvalidVenueError,
    InvalidVoteChoiceError,
)
from modules.gymkhana.domain.polls import (
    is_student_targeted,
    validate_poll_choices,
    validate_poll_vote_choice,
)
from modules.gymkhana.domain.scheduling import (
    CONFIGURED_VENUES,
    check_slot_overlap,
    validate_time_slot,
    validate_venue,
)
from modules.gymkhana.domain.state_machine import (
    ClubEstablishmentStateMachine,
    ClubMembershipStateMachine,
    PollStateMachine,
)

# --- Club Establishment State Machine (BW-GYM-03, BR-GYM-004) ---

def test_club_establishment_create_and_approve():
    next_state = ClubEstablishmentStateMachine.transition(None, "create", "student_admin")
    assert next_state == "open"

    final_state = ClubEstablishmentStateMachine.transition("open", "approve", "student_admin")
    assert final_state == "confirmed"


def test_club_establishment_disallows_non_admin():
    with pytest.raises(ActorNotAllowed):
        ClubEstablishmentStateMachine.transition(None, "create", "student")

    with pytest.raises(ActorNotAllowed):
        ClubEstablishmentStateMachine.transition("open", "approve", "club_head")


def test_club_establishment_invalid_transitions():
    with pytest.raises(InvalidTransition):
        ClubEstablishmentStateMachine.transition("confirmed", "approve", "student_admin")

    with pytest.raises(InvalidTransition):
        ClubEstablishmentStateMachine.transition("open", "create", "student_admin")


# --- Club Membership State Machine (BW-GYM-01, BR-GYM-007, BR-GYM-011) ---

def test_membership_apply_and_approve():
    next_state = ClubMembershipStateMachine.transition(
        None, "apply", "student", guards={"club_is_confirmed": True}
    )
    assert next_state == "open"

    final_state = ClubMembershipStateMachine.transition(
        "open", "approve", "club_head", guards={"actor_is_club_head": True}
    )
    assert final_state == "confirmed"


def test_membership_apply_fails_if_club_not_confirmed():
    with pytest.raises(GuardFailed):
        ClubMembershipStateMachine.transition(
            None, "apply", "student", guards={"club_is_confirmed": False}
        )


def test_membership_approve_fails_if_not_club_head():
    with pytest.raises(GuardFailed):
        ClubMembershipStateMachine.transition(
            "open", "approve", "club_head", guards={"actor_is_club_head": False}
        )


def test_membership_disallows_invalid_actors():
    with pytest.raises(ActorNotAllowed):
        ClubMembershipStateMachine.transition(
            None, "apply", "faculty", guards={"club_is_confirmed": True}
        )


# --- Poll State Machine (BW-GYM-02, BR-GYM-014) ---

def test_poll_create_vote_and_expire():
    s1 = PollStateMachine.transition(None, "create", "club_head")
    assert s1 == "active"

    s2 = PollStateMachine.transition("active", "vote", "student", guards={"is_unexpired": True})
    assert s2 == "active"

    s3 = PollStateMachine.transition("active", "expire", "system")
    assert s3 == "expired"


def test_poll_vote_fails_if_expired():
    with pytest.raises(GuardFailed):
        PollStateMachine.transition("active", "vote", "student", guards={"is_unexpired": False})


# --- Scheduling Validation (BR-GYM-005, BR-GYM-006, BR-GYM-020) ---

def test_configured_venues_validation():
    for v in CONFIGURED_VENUES:
        validate_venue(v)

    with pytest.raises(InvalidVenueError):
        validate_venue("Unknown-Hall")

    with pytest.raises(InvalidVenueError):
        validate_venue("")


def test_booking_time_slot_validation():
    t1 = datetime.time(9, 0)
    t2 = datetime.time(10, 0)
    validate_time_slot(t1, t2)

    with pytest.raises(InvalidTimeRangeError):
        validate_time_slot(t2, t1)

    with pytest.raises(InvalidTimeRangeError):
        validate_time_slot(t1, t1)


def test_check_slot_overlap():
    s1, e1 = datetime.time(10, 0), datetime.time(12, 0)
    s2, e2 = datetime.time(11, 0), datetime.time(13, 0)
    assert check_slot_overlap(s1, e1, s2, e2) is True

    # Adjacent slots do not overlap
    s3, e3 = datetime.time(12, 0), datetime.time(13, 0)
    assert check_slot_overlap(s1, e1, s3, e3) is False

    # Disjoint slots do not overlap
    s4, e4 = datetime.time(14, 0), datetime.time(15, 0)
    assert check_slot_overlap(s1, e1, s4, e4) is False


# --- Poll Domain Validation (BR-GYM-012, BR-GYM-013, BR-GYM-014) ---

def test_validate_poll_choices_valid():
    cleaned = validate_poll_choices(["Option A", "Option B", "Option C"])
    assert cleaned == ["Option A", "Option B", "Option C"]


def test_validate_poll_choices_too_few():
    with pytest.raises(InvalidPollChoicesError):
        validate_poll_choices(["Only One"])

    with pytest.raises(InvalidPollChoicesError):
        validate_poll_choices([])


def test_validate_poll_choices_duplicates_or_blank():
    with pytest.raises(InvalidPollChoicesError):
        validate_poll_choices(["Choice 1", "choice 1"])

    with pytest.raises(InvalidPollChoicesError):
        validate_poll_choices(["Choice 1", "  "])


def test_is_student_targeted_matching():
    targets = [
        {"batch_year": 2024, "discipline": "CSE"},
        {"batch_year": 2025, "discipline": "all"},
    ]
    # Matching specific discipline
    assert is_student_targeted(2024, "CSE", targets) is True
    assert is_student_targeted(2024, "cse", targets) is True

    # Non-matching discipline in 2024
    assert is_student_targeted(2024, "ECE", targets) is False

    # Matching 'all' discipline in 2025
    assert is_student_targeted(2025, "ECE", targets) is True
    assert is_student_targeted(2025, "ME", targets) is True

    # Non-matching batch year
    assert is_student_targeted(2023, "CSE", targets) is False
    assert is_student_targeted(None, "CSE", targets) is False


def test_validate_poll_vote_choice_service_invariant():
    # Matching choice and poll succeeds
    validate_poll_vote_choice(poll_id=1, choice_poll_id=1)

    # Inconsistent choice and poll raises InvalidVoteChoiceError
    with pytest.raises(InvalidVoteChoiceError):
        validate_poll_vote_choice(poll_id=1, choice_poll_id=2)
