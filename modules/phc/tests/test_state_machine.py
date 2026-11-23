"""Every move not in a transition table is refused, enumerated from the table itself."""
import itertools

import pytest

from modules.phc.domain.state_machine import (
    CLAIM_TRANSITIONS,
    REQUISITION_TRANSITIONS,
    ClaimStatus,
    IllegalTransition,
    RequisitionStatus,
    events_for,
    resolve,
)

CLAIM_STATES = [code for code, _ in ClaimStatus.CHOICES]
REQ_STATES = [code for code, _ in RequisitionStatus.CHOICES]
CLAIM_PERMS = sorted({t.permission for t in CLAIM_TRANSITIONS} | {"phc.claim.create"})
REQ_PERMS = sorted({t.permission for t in REQUISITION_TRANSITIONS}
                   | {"phc.requisition.create"})
CLAIM_EVENTS = sorted({t.event for t in CLAIM_TRANSITIONS})
REQ_EVENTS = sorted({t.event for t in REQUISITION_TRANSITIONS})


def _legal(table):
    return {(t.source, t.event, t.permission): t.target for t in table}


# BW-PHC-01
def test_claim_happy_path_bw_phc_01():
    path = [("forward", "phc.claim.review"), ("verify", "phc.claim.update"),
            ("approve", "phc.claim.approve"), ("pay", "phc.claim.update")]
    state = ClaimStatus.PENDING_PHC_REVIEW
    for event, perm in path:
        state = resolve(CLAIM_TRANSITIONS, state, event, {perm}).target
    assert state == ClaimStatus.REIMBURSED


# BW-PHC-02
def test_claim_rejected_at_sanction_bw_phc_02():
    move = resolve(CLAIM_TRANSITIONS, ClaimStatus.PENDING_SANCTION, "reject",
                   {"phc.claim.approve"})
    assert move.target == ClaimStatus.REJECTED


# BW-PHC-03, BW-PHC-04
def test_requisition_paths_bw_phc_03_bw_phc_04():
    approved = resolve(REQUISITION_TRANSITIONS, RequisitionStatus.PENDING_APPROVAL, "approve",
                       {"phc.requisition.approve"}).target
    assert resolve(REQUISITION_TRANSITIONS, approved, "fulfill",
                   {"phc.requisition.update"}).target == RequisitionStatus.FULFILLED
    assert resolve(REQUISITION_TRANSITIONS, RequisitionStatus.PENDING_APPROVAL, "reject",
                   {"phc.requisition.approve"}).target == RequisitionStatus.REJECTED


# CW-PHC-01
@pytest.mark.parametrize(("state", "event", "perm"),
                         list(itertools.product(CLAIM_STATES, CLAIM_EVENTS, CLAIM_PERMS)))
def test_every_claim_move_outside_the_table_is_refused_cw_phc_01(state, event, perm):
    legal = _legal(CLAIM_TRANSITIONS)
    if (state, event, perm) in legal:
        assert resolve(CLAIM_TRANSITIONS, state, event, {perm}).target == legal[
            (state, event, perm)]
    else:
        with pytest.raises(IllegalTransition):
            resolve(CLAIM_TRANSITIONS, state, event, {perm})


# CW-PHC-02
@pytest.mark.parametrize(("state", "event", "perm"),
                         list(itertools.product(REQ_STATES, REQ_EVENTS, REQ_PERMS)))
def test_every_requisition_move_outside_the_table_is_refused_cw_phc_02(state, event, perm):
    legal = _legal(REQUISITION_TRANSITIONS)
    if (state, event, perm) in legal:
        assert resolve(REQUISITION_TRANSITIONS, state, event, {perm}).target == legal[
            (state, event, perm)]
    else:
        with pytest.raises(IllegalTransition):
            resolve(REQUISITION_TRANSITIONS, state, event, {perm})


# PHC-BR-14
def test_terminal_states_have_no_way_out_phc_br_14():
    every = {t.permission for t in CLAIM_TRANSITIONS}
    for state in ClaimStatus.TERMINAL:
        assert events_for(CLAIM_TRANSITIONS, state, every) == []
    every = {t.permission for t in REQUISITION_TRANSITIONS}
    for state in RequisitionStatus.TERMINAL:
        assert events_for(REQUISITION_TRANSITIONS, state, every) == []


# PHC-BR-08
def test_review_and_verification_have_only_a_forward_path_phc_br_08():
    every = {t.permission for t in CLAIM_TRANSITIONS}
    assert events_for(CLAIM_TRANSITIONS, ClaimStatus.PENDING_PHC_REVIEW, every) == ["forward"]
    assert events_for(CLAIM_TRANSITIONS, ClaimStatus.PENDING_ACCOUNTS, every) == ["verify"]


# PHC-BR-10
def test_only_the_authority_may_decide_a_requisition_phc_br_10():
    assert events_for(REQUISITION_TRANSITIONS, RequisitionStatus.PENDING_APPROVAL,
                      {"phc.requisition.update", "phc.requisition.create"}) == []
