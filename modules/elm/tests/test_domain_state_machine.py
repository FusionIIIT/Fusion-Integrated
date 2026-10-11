"""Pure Python domain tests for workflow state transitions and state machines."""
from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain.constants import (
    ApplicationStatus,
    CancellationOutcome,
    ExtensionOutcome,
    ExtensionStatus,
    LeaveCategory,
    RecommendationOutcome,
    ResumptionStatus,
    SanctionDecision,
)
from modules.elm.domain.state_machine import (
    determine_resumption_outcome,
    get_initial_submission_status,
    transition_cancellation_establishment,
    transition_cancellation_final,
    transition_cancellation_request,
    transition_cancellation_unit_head,
    transition_establishment_routing,
    transition_extension_final,
    transition_extension_unit_head,
    transition_final_sanction,
    transition_substitute_replace,
    transition_substitute_response,
    transition_unit_head_review,
    transition_withdrawal,
)


def test_initial_submission_state():
    """Initial state depending on substitute and director role."""
    # With substitute -> AWAITING_SUBSTITUTE
    s1 = get_initial_submission_status(requires_substitute=True, applicant_is_director=False)
    assert s1 == ApplicationStatus.AWAITING_SUBSTITUTE

    # Without substitute, normal applicant -> AWAITING_UNIT_HEAD
    s2 = get_initial_submission_status(requires_substitute=False, applicant_is_director=False)
    assert s2 == ApplicationStatus.AWAITING_UNIT_HEAD

    # Director as applicant -> AWAITING_DIRECTOR (self-sanction bypass)
    s3 = get_initial_submission_status(requires_substitute=False, applicant_is_director=True)
    assert s3 == ApplicationStatus.AWAITING_DIRECTOR


def test_substitute_response_flow():
    """CW-EL-01: Substitute accept or decline."""
    # Accepted -> Unit Head
    s_acc = transition_substitute_response(
        ApplicationStatus.AWAITING_SUBSTITUTE,
        accepted=True,
        applicant_is_director=False,
    )
    assert s_acc == ApplicationStatus.AWAITING_UNIT_HEAD

    # Accepted for director -> Awaiting Director
    s_acc_dir = transition_substitute_response(
        ApplicationStatus.AWAITING_SUBSTITUTE,
        accepted=True,
        applicant_is_director=True,
    )
    assert s_acc_dir == ApplicationStatus.AWAITING_DIRECTOR

    # Declined -> Applicant Action Required
    s_dec = transition_substitute_response(
        ApplicationStatus.AWAITING_SUBSTITUTE,
        accepted=False,
    )
    assert s_dec == ApplicationStatus.APPLICANT_ACTION_REQUIRED

    # Replace substitute -> Awaiting substitute again
    s_rep = transition_substitute_replace(ApplicationStatus.APPLICANT_ACTION_REQUIRED)
    assert s_rep == ApplicationStatus.AWAITING_SUBSTITUTE


def test_unit_head_review_terminal_for_cl_rh():
    """BR-EL-016: Unit head is final sanctioning authority for CL and RH."""
    # CL approved by Unit Head -> APPROVED
    res_cl = transition_unit_head_review(
        ApplicationStatus.AWAITING_UNIT_HEAD,
        LeaveCategory.CL,
        outcome=RecommendationOutcome.APPROVE.value,
    )
    assert res_cl == ApplicationStatus.APPROVED

    # RH rejected by Unit Head -> REJECTED
    res_rh = transition_unit_head_review(
        ApplicationStatus.AWAITING_UNIT_HEAD,
        LeaveCategory.RH,
        outcome=RecommendationOutcome.REJECT.value,
    )
    assert res_rh == ApplicationStatus.REJECTED


def test_unit_head_review_higher_sanction_routing():
    """BR-EL-017: EL, COL, VL, SCL route higher."""
    # EL recommended with establishment enabled -> AWAITING_ESTABLISHMENT
    res_el_estt = transition_unit_head_review(
        ApplicationStatus.AWAITING_UNIT_HEAD,
        LeaveCategory.EL,
        outcome=RecommendationOutcome.RECOMMENDED.value,
        requires_establishment=True,
    )
    assert res_el_estt == ApplicationStatus.AWAITING_ESTABLISHMENT

    # Forwarded through Establishment -> AWAITING_FINAL_DECISION
    res_final = transition_establishment_routing(ApplicationStatus.AWAITING_ESTABLISHMENT)
    assert res_final == ApplicationStatus.AWAITING_FINAL_DECISION

    # Final decision -> APPROVED
    res_sanction = transition_final_sanction(
        ApplicationStatus.AWAITING_FINAL_DECISION,
        decision=SanctionDecision.APPROVE.value,
    )
    assert res_sanction == ApplicationStatus.APPROVED


def test_immediate_withdrawal_from_any_pending_state():
    """BR-EL-022: Immediate withdrawal is permitted from any pre-final state."""
    pending_states = [
        ApplicationStatus.DRAFT,
        ApplicationStatus.AWAITING_SUBSTITUTE,
        ApplicationStatus.APPLICANT_ACTION_REQUIRED,
        ApplicationStatus.AWAITING_UNIT_HEAD,
        ApplicationStatus.AWAITING_DIRECTOR,
        ApplicationStatus.AWAITING_ESTABLISHMENT,
        ApplicationStatus.AWAITING_FINAL_DECISION,
    ]
    for st in pending_states:
        withdrawn = transition_withdrawal(st)
        assert withdrawn == ApplicationStatus.WITHDRAWN

    # Terminal state withdrawal raises
    for term in (ApplicationStatus.APPROVED, ApplicationStatus.REJECTED, ApplicationStatus.CANCELLED):
        with pytest.raises(ValueError, match="Cannot withdraw"):
            transition_withdrawal(term)


def test_cancellation_workflow():
    """CW-EL-02 / BR-EL-023: Cancellation only for approved leave before start date."""
    leave_start = date(2026, 11, 1)

    # Requested before start date: Allowed -> CANCELLATION_PENDING_UNIT_HEAD
    req = transition_cancellation_request(
        ApplicationStatus.APPROVED,
        start_date=leave_start,
        today=date(2026, 10, 20),
    )
    assert req == ApplicationStatus.CANCELLATION_PENDING_UNIT_HEAD

    # Requested on or after start date: Disallowed
    with pytest.raises(ValueError, match="only permitted before"):
        transition_cancellation_request(
            ApplicationStatus.APPROVED,
            start_date=leave_start,
            today=date(2026, 11, 1),
        )

    # Unit head approves CL cancellation -> CANCELLED
    canc_cl = transition_cancellation_unit_head(
        ApplicationStatus.CANCELLATION_PENDING_UNIT_HEAD,
        category=LeaveCategory.CL,
        outcome=CancellationOutcome.APPROVE.value,
    )
    assert canc_cl == ApplicationStatus.CANCELLED

    # Higher leave cancellation forwarded to establishment -> final decision
    canc_el_estt = transition_cancellation_unit_head(
        ApplicationStatus.CANCELLATION_PENDING_UNIT_HEAD,
        category=LeaveCategory.EL,
        outcome=CancellationOutcome.RECOMMENDED.value,
        requires_establishment=True,
    )
    assert canc_el_estt == ApplicationStatus.CANCELLATION_PENDING_ESTABLISHMENT

    canc_fwd = transition_cancellation_establishment(canc_el_estt)
    assert canc_fwd == ApplicationStatus.CANCELLATION_PENDING_FINAL

    canc_final = transition_cancellation_final(
        canc_fwd,
        decision=SanctionDecision.APPROVE.value,
    )
    assert canc_final == ApplicationStatus.CANCELLED


def test_extension_workflow():
    """CW-EL-03 / BR-EL-025: Extension of ongoing leave."""
    ext_unit = transition_extension_unit_head(
        ExtensionStatus.AWAITING_UNIT_HEAD,
        outcome=ExtensionOutcome.RECOMMENDED.value,
        requires_establishment=False,
    )
    assert ext_unit == ExtensionStatus.AWAITING_FINAL_DECISION

    ext_approved = transition_extension_final(
        ExtensionStatus.AWAITING_FINAL_DECISION,
        decision=SanctionDecision.APPROVE.value,
    )
    assert ext_approved == ExtensionStatus.APPROVED


def test_resumption_outcome_and_balance_adjustment():
    """CW-EL-04 / BR-EL-028: Normal, Early (credit), Late (debit)."""
    approved_end = date(2026, 10, 20)

    # 1. Normal return on next working day (2026-10-21)
    ret_type, outcome_status = determine_resumption_outcome(approved_end, date(2026, 10, 21))
    assert ret_type == "normal"
    assert outcome_status == ResumptionStatus.REVIEWED_NO_ADJUSTMENT

    # 2. Early return on 2026-10-18 (before approved end date)
    ret_early, status_early = determine_resumption_outcome(approved_end, date(2026, 10, 18))
    assert ret_early == "early"
    assert status_early == ResumptionStatus.REVIEWED_EARLY_ADJUSTED

    # 3. Late return on 2026-10-25
    ret_late, status_late = determine_resumption_outcome(approved_end, date(2026, 10, 25))
    assert ret_late == "late"
    assert status_late == ResumptionStatus.REVIEWED_LATE_ADJUSTED
