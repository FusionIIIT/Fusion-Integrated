"""Pure domain tests for SPACS state machine and transitions."""

import pytest
from modules.spacs.domain import state_machine as sm
from modules.spacs.domain.errors import InvalidTransitionError


def test_scholarship_happy_path_transitions():
    t1 = sm.resolve_application_transition(sm.DRAFT, "submit", "student")
    assert t1.target == sm.SUBMITTED

    t2 = sm.resolve_application_transition(sm.SUBMITTED, "open_verification", "spacs_assistant")
    assert t2.target == sm.UNDER_VERIFICATION

    t3 = sm.resolve_application_transition(sm.UNDER_VERIFICATION, "mark_verified", "spacs_assistant")
    assert t3.target == sm.VERIFIED

    t4 = sm.resolve_application_transition(sm.VERIFIED, "open_decision", "spacs_convener")
    assert t4.target == sm.UNDER_CONVENER_REVIEW

    t5 = sm.resolve_application_transition(sm.UNDER_CONVENER_REVIEW, "approve", "spacs_convener")
    assert t5.target == sm.APPROVED


def test_correction_and_resubmission_traversal():
    t1 = sm.resolve_application_transition(sm.UNDER_VERIFICATION, "request_correction", "spacs_assistant")
    assert t1.target == sm.CORRECTION_REQUIRED

    t2 = sm.resolve_application_transition(sm.CORRECTION_REQUIRED, "resubmit", "student")
    assert t2.target == sm.RESUBMITTED

    t3 = sm.resolve_application_transition(sm.RESUBMITTED, "mark_verified", "spacs_assistant")
    assert t3.target == sm.VERIFIED


def test_withdrawal_from_withdrawable_states():
    for state in [sm.SUBMITTED, sm.UNDER_VERIFICATION, sm.CORRECTION_REQUIRED, sm.RESUBMITTED, sm.VERIFIED]:
        t = sm.resolve_application_transition(state, "withdraw", "student")
        assert t.target == sm.WITHDRAWN


def test_illegal_transition_raises():
    with pytest.raises(InvalidTransitionError):
        # Cannot jump directly from draft to approved
        sm.resolve_application_transition(sm.DRAFT, "approve", "spacs_convener")

    with pytest.raises(InvalidTransitionError):
        # Assistant cannot approve
        sm.resolve_application_transition(sm.UNDER_VERIFICATION, "approve", "spacs_assistant")


def test_award_cycle_transitions():
    t1 = sm.resolve_award_transition(sm.AWARD_CYCLE_OPEN, "prepare_pool", "spacs_convener")
    assert t1.target == sm.CANDIDATE_POOL_PREPARED

    t2 = sm.resolve_award_transition(sm.CANDIDATE_POOL_PREPARED, "begin_evaluation", "award_evaluation_committee")
    assert t2.target == sm.UNDER_COMMITTEE_EVALUATION

    t3 = sm.resolve_award_transition(sm.UNDER_COMMITTEE_EVALUATION, "record_committee_result", "award_evaluation_committee")
    assert t3.target == sm.COMMITTEE_RESULT_RECORDED

    t4 = sm.resolve_award_transition(sm.COMMITTEE_RESULT_RECORDED, "record_approved_outcome", "spacs_convener")
    assert t4.target == sm.READY_FOR_PUBLICATION

    t5 = sm.resolve_award_transition(sm.READY_FOR_PUBLICATION, "publish_results", "spacs_convener")
    assert t5.target == sm.PUBLISHED
