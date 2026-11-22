"""Domain tests for SPACS: pure Python, zero database, running in milliseconds."""
import pytest

from modules.spacs.domain import award_state_machine as asm
from modules.spacs.domain import state_machine as sm
from modules.spacs.domain.eligibility import evaluate_criteria
from modules.spacs.domain.renewal import evaluate_renewal_eligibility


# --- Scholarship Application State Machine Tests ---

def test_application_transition_table_completeness():
    declared = {(t.frm, t.to) for t in sm.TRANSITIONS}
    for frm in sm.ALL_STATES:
        for to in sm.ALL_STATES:
            assert sm.is_legal(frm, to) is ((frm, to) in declared)


def test_terminal_application_states_have_no_exits():
    for s in sm.TERMINAL:
        assert sm.allowed_targets(s) == []


def test_illegal_transition_raises_invalid_transition():
    with pytest.raises(sm.InvalidTransition):
        sm.resolve(sm.DRAFT, sm.APPROVED)


def test_assistant_cannot_approve_or_reject():
    """BR-SPACS-006 & BR-SPACS-018: Assistant cannot make final sanction/rejection."""
    with pytest.raises(sm.ActorNotAllowed):
        sm.resolve(sm.UNDER_CONVENER_REVIEW, sm.APPROVED, sm.ASSISTANT)

    with pytest.raises(sm.ActorNotAllowed):
        sm.resolve(sm.UNDER_CONVENER_REVIEW, sm.REJECTED, sm.ASSISTANT)


def test_convener_can_approve_and_reject():
    """BR-SPACS-018: Convener is the final decision authority."""
    t_app = sm.resolve(sm.UNDER_CONVENER_REVIEW, sm.APPROVED, sm.CONVENER)
    assert t_app.to == sm.APPROVED

    t_rej = sm.resolve(sm.UNDER_CONVENER_REVIEW, sm.REJECTED, sm.CONVENER)
    assert t_rej.to == sm.REJECTED


def test_withdrawable_states():
    """BR-SPACS-009: Withdrawal permitted only in pre-final withdrawable states."""
    for s in sm.WITHDRAWABLE:
        assert sm.is_legal(s, sm.WITHDRAWN, sm.STUDENT) is True

    # Terminal states cannot be withdrawn
    for s in sm.TERMINAL:
        assert sm.is_legal(s, sm.WITHDRAWN, sm.STUDENT) is False


def test_editable_states():
    """BR-SPACS-010 & AFR-SPACS-031: Application editable only in configured editable states."""
    assert sm.DRAFT in sm.EDITABLE
    assert sm.SUBMITTED in sm.EDITABLE
    assert sm.CORRECTION_REQUIRED in sm.EDITABLE
    assert sm.APPROVED not in sm.EDITABLE
    assert sm.REJECTED not in sm.EDITABLE


# --- Award State Machine Tests ---

def test_award_cycle_progression():
    """CW-SPACS-03: Convocation award lifecycle states."""
    assert asm.is_legal_award_transition(asm.OPEN, asm.POOL_PREPARED, asm.CONVENER) is True
    assert asm.is_legal_award_transition(asm.POOL_PREPARED, asm.UNDER_EVALUATION, asm.COMMITTEE) is True
    assert asm.is_legal_award_transition(asm.UNDER_EVALUATION, asm.RESULT_RECORDED, asm.COMMITTEE) is True
    assert asm.is_legal_award_transition(asm.RESULT_RECORDED, asm.READY_FOR_PUBLICATION, asm.CONVENER) is True
    assert asm.is_legal_award_transition(asm.READY_FOR_PUBLICATION, asm.PUBLISHED, asm.CONVENER) is True


def test_award_publication_guarded_by_approval():
    """AFR-SPACS-046: Results cannot jump straight to PUBLISHED without READY_FOR_PUBLICATION."""
    with pytest.raises(asm.InvalidAwardTransition):
        asm.resolve_award_transition(asm.RESULT_RECORDED, asm.PUBLISHED)


def test_award_terminal_state():
    assert asm.allowed_award_targets(asm.PUBLISHED) == []


# --- Eligibility Rules Engine Tests (BR-SPACS-001) ---

FACTS = {
    "cpi": 8.0,
    "parental_income": 450000,
    "discipline": "CSE",
    "batch_year": 2023,
    "category": "GEN",
    "active_backlogs": 0,
    "gender": "male",
}


def test_empty_criteria_passes():
    res = evaluate_criteria({}, FACTS)
    assert res.is_eligible is True


def test_cpi_check():
    res_pass = evaluate_criteria({"min_cpi": 7.5}, FACTS)
    assert res_pass.is_eligible is True

    res_fail = evaluate_criteria({"min_cpi": 8.5}, FACTS)
    assert res_fail.is_eligible is False
    assert any("CPI" in r for r in res_fail.failed_reasons)


def test_income_ceiling_check():
    res_pass = evaluate_criteria({"max_parental_income": 500000}, FACTS)
    assert res_pass.is_eligible is True

    res_fail = evaluate_criteria({"max_parental_income": 400000}, FACTS)
    assert res_fail.is_eligible is False
    assert any("Parental income" in r for r in res_fail.failed_reasons)


def test_discipline_filter():
    res_pass = evaluate_criteria({"disciplines": ["CSE", "ECE"]}, FACTS)
    assert res_pass.is_eligible is True

    res_fail = evaluate_criteria({"disciplines": ["ME", "Design"]}, FACTS)
    assert res_fail.is_eligible is False


def test_fail_closed_on_missing_facts():
    res = evaluate_criteria({"min_cpi": 7.0, "max_parental_income": 500000}, {})
    assert res.is_eligible is False
    assert len(res.failed_reasons) == 2


# --- Renewal Eligibility Tests (CFR-SPACS-012, BR-SPACS-017) ---

def test_renewal_requires_approved_prior_status():
    res = evaluate_renewal_eligibility(
        is_renewable=True,
        prior_application_status="rejected",
        renewal_window_open=True,
        renewal_rules={"min_cpi": 6.5},
        current_facts={"cpi": 8.0},
    )
    assert res.can_renew is False
    assert any("approved" in r for r in res.reasons)


def test_renewal_closed_window():
    res = evaluate_renewal_eligibility(
        is_renewable=True,
        prior_application_status="approved",
        renewal_window_open=False,
        renewal_rules={"min_cpi": 6.5},
        current_facts={"cpi": 8.0},
    )
    assert res.can_renew is False
    assert any("closed" in r for r in res.reasons)


def test_successful_renewal_evaluation():
    res = evaluate_renewal_eligibility(
        is_renewable=True,
        prior_application_status="approved",
        renewal_window_open=True,
        renewal_rules={"min_cpi": 6.5, "max_backlogs": 0, "max_years": 4},
        current_facts={"cpi": 7.2, "active_backlogs": 0},
    )
    assert res.can_renew is True
    assert len(res.reasons) == 0
    assert "grade_sheet" in res.refreshed_evidence_required
