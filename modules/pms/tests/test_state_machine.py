"""The transition tables, enumerated: every move not in a table is refused (PMS-AFR-225)."""
import itertools

import pytest

from modules.pms.domain import state_machine as sm
from modules.pms.domain.errors import ActorNotAllowed, InvalidTransition


def _all_cases(machine):
    states = sorted(machine.states | {sm.NEW})
    return list(itertools.product(states, sorted(machine.events), sm.ACTORS))


# PMS-AFR-225
@pytest.mark.parametrize("machine", sm.MACHINES, ids=lambda m: m.name)
def test_every_illegal_move_is_refused_pms_afr_225(machine):
    for frm, event, actor in _all_cases(machine):
        edge = next((t for t in machine.transitions if t.frm == frm and t.event == event),
                    None)
        if edge is None:
            with pytest.raises(InvalidTransition):
                machine.resolve(frm, event, actor)
        elif actor not in edge.actors:
            with pytest.raises(ActorNotAllowed):
                machine.resolve(frm, event, actor)
        else:
            assert machine.resolve(frm, event, actor).to == edge.to


@pytest.mark.parametrize("machine", sm.MACHINES, ids=lambda m: m.name)
def test_terminal_states_have_no_way_out(machine):
    for t in machine.transitions:
        assert t.frm not in machine.terminal


def test_a_duplicate_edge_cannot_be_declared():
    t = sm.Transition("a", "go", "b", frozenset({sm.SYSTEM}))
    with pytest.raises(ValueError):
        sm.Machine("x", (t, t))


def test_an_edge_out_of_a_terminal_state_cannot_be_declared():
    with pytest.raises(ValueError):
        sm.Machine("x", (sm.Transition("end", "go", "b", frozenset({sm.SYSTEM})),),
                   terminal=frozenset({"end"}))


# BW-PMS-01
def test_bw_pms_01_initial_review_approval_path():
    assert sm.APPLICATION.resolve(sm.DRAFT, "submit", sm.APPLICANT).to == sm.SUBMITTED
    assert sm.APPLICATION.resolve(sm.SUBMITTED, "assign_director", sm.PCC_ADMIN).to \
        == sm.UNDER_REVIEW
    assert sm.APPLICATION.resolve(sm.UNDER_REVIEW, "approve", sm.DIRECTOR).to == sm.APPROVED


# BW-PMS-02
def test_bw_pms_02_revision_path():
    assert sm.APPLICATION.resolve(sm.UNDER_REVIEW, "request_revision", sm.DIRECTOR).to \
        == sm.NEEDS_REVISION
    assert sm.APPLICATION.resolve(sm.NEEDS_REVISION, "resubmit", sm.APPLICANT).to \
        == sm.RESUBMITTED
    assert sm.APPLICATION.resolve(sm.RESUBMITTED, "assign_director", sm.PCC_ADMIN).to \
        == sm.UNDER_REVIEW


@pytest.mark.parametrize(("event", "to"), [
    ("appeal_remanded", sm.NEEDS_REVISION),            # BW-PMS-03
    ("appeal_upheld", sm.REJECTION_UPHELD),            # BW-PMS-04
    ("appeal_modified_approve", sm.APPROVED),          # BW-PMS-05
    ("appeal_modified_revise", sm.NEEDS_REVISION),     # BW-PMS-05
])
# BW-PMS-03 BW-PMS-04 BW-PMS-05
def test_bw_pms_03_04_05_appeal_paths(event, to):
    assert sm.APPLICATION.resolve(sm.REJECTED, "appeal", sm.APPLICANT).to \
        == sm.APPEAL_SUBMITTED
    assert sm.APPLICATION.resolve(sm.APPEAL_SUBMITTED, event, sm.SYSTEM).to == to


# BW-PMS-06 BW-PMS-07
def test_bw_pms_06_07_attorney_paths():
    assert sm.ASSIGNMENT.resolve(sm.NEW, "offer", sm.PCC_ADMIN).to == sm.OFFERED
    assert sm.ASSIGNMENT.resolve(sm.OFFERED, "accept", sm.ATTORNEY).to == sm.ACCEPTED
    assert sm.ASSIGNMENT.resolve(sm.OFFERED, "decline", sm.ATTORNEY).to == sm.DECLINED
    assert sm.APPLICATION.resolve(sm.APPROVED, "attorney_declined", sm.SYSTEM).to \
        == sm.PENDING_REVIEW
    assert sm.APPLICATION.resolve(sm.PENDING_REVIEW, "attorney_accepted", sm.SYSTEM).to \
        == sm.ATTORNEY_ASSIGNED


# BW-PMS-08 BW-PMS-09 BW-PMS-10
def test_bw_pms_08_09_10_budget_paths():
    assert sm.BUDGET.resolve(sm.PROPOSED, "approve", sm.DIRECTOR).to == sm.BUDGET_APPROVED
    assert sm.BUDGET.resolve(sm.PROPOSED, "reject", sm.DIRECTOR).to == sm.BUDGET_REJECTED
    assert sm.BUDGET.resolve(sm.PROPOSED, "escalate", sm.DIRECTOR).to == sm.ESCALATED
    assert sm.BUDGET.resolve(sm.ESCALATED, "route", sm.PCC_ADMIN).to == sm.ESCALATION_TRACKED


# BW-PMS-11
def test_bw_pms_11_filing_only_by_the_attorney():
    assert sm.APPLICATION.resolve(sm.ATTORNEY_ASSIGNED, "file", sm.ATTORNEY).to == sm.FILED
    with pytest.raises(ActorNotAllowed):
        sm.APPLICATION.resolve(sm.ATTORNEY_ASSIGNED, "file", sm.PCC_ADMIN)
    with pytest.raises(InvalidTransition):
        sm.APPLICATION.resolve(sm.APPROVED, "file", sm.ATTORNEY)


# BW-PMS-12 BW-PMS-13
def test_bw_pms_12_13_office_action_paths():
    assert sm.OFFICE_ACTION.resolve(sm.RECORDED, "prepare_for_applicant", sm.ATTORNEY).to \
        == sm.AWAITING_APPLICANT
    assert sm.OFFICE_ACTION.resolve(sm.AWAITING_APPLICANT, "applicant_approve",
                                    sm.APPLICANT).to == sm.APPLICANT_APPROVED
    assert sm.OFFICE_ACTION.resolve(sm.RECORDED, "prepare_ready", sm.ATTORNEY).to \
        == sm.RESPONSE_READY
    with pytest.raises(InvalidTransition):
        sm.OFFICE_ACTION.resolve(sm.AWAITING_APPLICANT, "submit", sm.ATTORNEY)


# BW-PMS-14 BW-PMS-15
def test_bw_pms_14_15_maintenance_paths():
    assert sm.MAINTENANCE.resolve(sm.SCHEDULED, "request", sm.ATTORNEY).to \
        == sm.DECISION_REQUESTED
    assert sm.MAINTENANCE.resolve(sm.DECISION_REQUESTED, "renew", sm.DIRECTOR).to \
        == sm.RENEW_APPROVED
    assert sm.MAINTENANCE.resolve(sm.DECISION_REQUESTED, "do_not_renew", sm.DIRECTOR).to \
        == sm.DO_NOT_RENEW
    with pytest.raises(InvalidTransition):
        sm.MAINTENANCE.resolve(sm.SCHEDULED, "record_action", sm.ATTORNEY)


# BW-PMS-16 CW-PMS-05
def test_bw_pms_16_cw_pms_05_withdrawal_from_exactly_the_seven_candidates():
    origins = {t.frm for t in sm.APPLICATION.transitions if t.event == "withdraw"}
    assert origins == set(sm.WITHDRAWAL_CANDIDATES)
    assert len(sm.WITHDRAWAL_CANDIDATES) == 7


# CW-PMS-01 BR-PMS-029
def test_cw_pms_01_review_disposition_has_three_decisions_br_pms_029():
    decisions = {t.event for t in sm.APPLICATION.transitions if t.frm == sm.UNDER_REVIEW
                 and sm.DIRECTOR in t.actors}
    assert decisions == {"approve", "request_revision", "reject"}


# CW-PMS-02 PMS-AFR-227
def test_cw_pms_02_budget_and_attorney_run_in_parallel_pms_afr_227():
    assert sm.ATTORNEY_ASSIGNABLE <= sm.BUDGET_STATUSES


# CW-PMS-03 CW-PMS-04
def test_cw_pms_03_cw_pms_04_composites_are_covered():
    assert sm.OFFICE_ACTION.events >= {"prepare_for_applicant", "prepare_ready",
                                       "applicant_approve", "submit"}
    assert sm.MAINTENANCE.events >= {"request", "renew", "do_not_renew", "record_action"}


# BR-PMS-095
def test_appeal_outcomes_are_exactly_three_br_pms_095():
    assert sm.APPEAL.events == {"uphold", "remand", "modify"}


# BR-PMS-038
def test_expiry_is_system_only_br_pms_038():
    with pytest.raises(ActorNotAllowed):
        sm.APPLICATION.resolve(sm.NEEDS_REVISION, "expire", sm.APPLICANT)


def test_events_for_lists_what_an_actor_may_do():
    assert sm.APPLICATION.events_for(sm.REJECTED, sm.APPLICANT) == ["appeal", "resubmit",
                                                                    "withdraw"]
    assert sm.APPLICATION.is_legal(sm.DRAFT, "submit")
    assert not sm.APPLICATION.is_legal(sm.DRAFT, "approve")


def test_error_messages_name_the_state_and_event():
    with pytest.raises(InvalidTransition) as exc:
        sm.APPLICATION.resolve(sm.WITHDRAWN, "submit", sm.APPLICANT)
    assert "withdrawn" in exc.value.message
    assert exc.value.code == "invalid_transition"
