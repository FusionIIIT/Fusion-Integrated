import pytest

from modules.elm.domain.errors import InvalidStateTransitionError
from modules.elm.domain.state_machine import (
    determine_initial_state,
    transition_establishment_routing,
    transition_final_sanction,
    transition_replacement_substitute,
    transition_substitute_response,
    transition_unit_head_review,
    transition_withdrawal,
)


def test_initial_state_derivation():
    # Substitute required takes precedence
    assert (
        determine_initial_state(substitute_required=True, is_director=False)
        == "awaiting_substitute"
    )
    assert (
        determine_initial_state(substitute_required=True, is_director=True) == "awaiting_substitute"
    )

    # No substitute, applicant is Director -> awaiting_director_self_sanction (BR-EL-020)
    assert (
        determine_initial_state(substitute_required=False, is_director=True)
        == "awaiting_director_self_sanction"
    )

    # Normal employee -> awaiting_unit_head
    assert (
        determine_initial_state(substitute_required=False, is_director=False)
        == "awaiting_unit_head"
    )


def test_substitute_response_and_decline_recovery():
    # Accept -> moves to Unit Head (or Director)
    assert (
        transition_substitute_response("awaiting_substitute", accepted=True, is_director=False)
        == "awaiting_unit_head"
    )
    assert (
        transition_substitute_response("awaiting_substitute", accepted=True, is_director=True)
        == "awaiting_director_self_sanction"
    )

    # Decline -> applicant action required (BR-EL-015)
    assert (
        transition_substitute_response("awaiting_substitute", accepted=False, is_director=False)
        == "applicant_action_required"
    )

    # Replacement nomination -> awaiting_substitute again (EL-UC-019)
    assert transition_replacement_substitute("applicant_action_required") == "awaiting_substitute"


def test_unit_head_final_authority_for_cl_rh():
    """BR-EL-016: Unit Head has final authority for CL and RH."""
    assert transition_unit_head_review("awaiting_unit_head", "CL", action="approve") == "approved"
    assert transition_unit_head_review("awaiting_unit_head", "RH", action="reject") == "rejected"

    # Cannot 'recommend' for CL/RH
    with pytest.raises(InvalidStateTransitionError):
        transition_unit_head_review("awaiting_unit_head", "CL", action="recommend")


def test_unit_head_recommendation_for_higher_sanction():
    """BR-EL-017: For SCL/EL/COL/VL, Unit Head records recommendation."""
    # Without establishment step
    assert (
        transition_unit_head_review(
            "awaiting_unit_head", "EL", action="recommend", establishment_configured=False
        )
        == "awaiting_final_sanction"
    )
    assert (
        transition_unit_head_review(
            "awaiting_unit_head", "EL", action="not_recommend", establishment_configured=False
        )
        == "awaiting_final_sanction"
    )

    # With establishment step (BR-EL-019)
    assert (
        transition_unit_head_review(
            "awaiting_unit_head", "EL", action="recommend", establishment_configured=True
        )
        == "awaiting_establishment"
    )
    assert transition_establishment_routing("awaiting_establishment") == "awaiting_final_sanction"


def test_final_sanction_decisions():
    """BR-EL-018, BR-EL-020: Sanctioning Authority decision."""
    assert transition_final_sanction("awaiting_final_sanction", action="approve") == "approved"
    assert transition_final_sanction("awaiting_final_sanction", action="reject") == "rejected"
    assert (
        transition_final_sanction("awaiting_director_self_sanction", action="approve") == "approved"
    )
    assert (
        transition_final_sanction("awaiting_director_self_sanction", action="reject") == "rejected"
    )


def test_immediate_withdrawal_from_all_pending_pre_final_states():
    """BR-EL-022, BR-EL-034: Withdrawal allowed from any valid pending state before final decision."""
    pending_states = [
        "awaiting_substitute",
        "applicant_action_required",
        "awaiting_unit_head",
        "awaiting_establishment",
        "awaiting_final_sanction",
        "awaiting_director_self_sanction",
    ]
    for s in pending_states:
        assert transition_withdrawal(s) == "withdrawn"

    # Terminal states cannot be withdrawn
    for terminal in ["approved", "rejected", "withdrawn", "cancelled"]:
        with pytest.raises(InvalidStateTransitionError):
            transition_withdrawal(terminal)
