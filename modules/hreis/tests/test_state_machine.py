import pytest

from modules.hreis.domain.state_machine import (
    APPROVING_AUTHORITY,
    DRAFT,
    EMPLOYEE,
    FINALIZED_ARCHIVED_CLOSED,
    PENDING_NEXT_AUTHORITY,
    REVIEWER_ASSIGNED_PENDING_REVIEW,
    ActorNotAllowed,
    GuardFailed,
    InvalidTransition,
    apply,
)


def test_leave_submission_requires_all_guards():
    with pytest.raises(GuardFailed, match="valid_required_fields"):
        apply("leave", DRAFT, "submit", EMPLOYEE, {})


def test_leave_submission_moves_to_current_authority():
    facts = {
        "valid_required_fields": True,
        "supported_leave_type": True,
        "balance_and_eligibility": True,
        "route_exists": True,
    }
    assert apply("leave", DRAFT, "submit", EMPLOYEE, facts) == "pending_current_authority"


def test_appraisal_can_repeat_configured_authority_traversals():
    facts = {
        "current_actor_is_authority": True,
        "is_not_request_owner": True,
        "configured_next_authority_exists": True,
    }
    assert (
        apply("appraisal", PENDING_NEXT_AUTHORITY, "forward", APPROVING_AUTHORITY, facts)
        == PENDING_NEXT_AUTHORITY
    )


def test_appraisal_finalizes_only_at_configured_final_authority():
    facts = {
        "current_actor_is_authority": True,
        "is_not_request_owner": True,
        "final_authority": True,
    }
    assert (
        apply("appraisal", REVIEWER_ASSIGNED_PENDING_REVIEW, "finalize", APPROVING_AUTHORITY, facts)
        == FINALIZED_ARCHIVED_CLOSED
    )


def test_appraisal_finalization_requires_final_authority():
    with pytest.raises(GuardFailed, match="final_authority"):
        apply(
            "appraisal",
            REVIEWER_ASSIGNED_PENDING_REVIEW,
            "finalize",
            APPROVING_AUTHORITY,
            {
                "current_actor_is_authority": True,
                "is_not_request_owner": True,
            },
        )


def test_wrong_actor_is_rejected():
    with pytest.raises(ActorNotAllowed):
        apply("leave", "pending_current_authority", "approve", EMPLOYEE, {})


def test_request_owner_cannot_approve_own_leave_request():
    with pytest.raises(GuardFailed, match="is_not_request_owner"):
        apply(
            "leave",
            "pending_current_authority",
            "approve",
            APPROVING_AUTHORITY,
            {
                "current_actor_is_authority": True,
                "is_not_request_owner": False,
                "final_authority": True,
            },
        )


def test_unspecified_ltc_return_transition_is_not_supported():
    with pytest.raises(InvalidTransition):
        apply("ltc", "rejected", "return", APPROVING_AUTHORITY, {})
