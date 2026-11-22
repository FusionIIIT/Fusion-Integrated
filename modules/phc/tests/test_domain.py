"""Pure Python domain unit tests (Zero database, milliseconds execution).

Tests domain state machines, validation rules, eligibility, and threshold evaluations.
"""
from datetime import date, timedelta
import pytest

from modules.phc.domain.entities import (
    DoctorAttendanceStatus,
    ReimbursementStatus,
    RequisitionStatus,
)
from modules.phc.domain.errors import (
    ClaimImmutableError,
    InvalidStateTransitionError,
    RequisitionNotApprovedError,
)
from modules.phc.domain.rules import (
    evaluate_claim_immutability,
    evaluate_claimant_eligibility,
    evaluate_prescription_requirement,
    evaluate_stock_threshold,
    evaluate_submission_window,
)
from modules.phc.domain.state_machine import (
    ReimbursementStateMachine,
    RequisitionStateMachine,
)


# --- Reimbursement State Machine & Business Rules ---

def test_reimbursement_state_machine_happy_path():
    sm = ReimbursementStateMachine()
    
    # 1. Forward from PHC
    s1 = sm.transition_phc_review_forward(ReimbursementStatus.PENDING_PHC_REVIEW.value)
    assert s1 == ReimbursementStatus.PENDING_ACCOUNTS_VERIFICATION

    # 2. Verify by Accounts
    s2 = sm.transition_accounts_verify(s1.value)
    assert s2 == ReimbursementStatus.PENDING_SANCTION

    # 3. Sanction by Authority (Approve)
    s3 = sm.transition_sanction_decision(s2.value, approve=True)
    assert s3 == ReimbursementStatus.APPROVED_FOR_PAYMENT

    # 4. Process Payment
    s4 = sm.transition_payment_process(s3.value)
    assert s4 == ReimbursementStatus.REIMBURSED


def test_reimbursement_rejections_and_invalid_transitions():
    sm = ReimbursementStateMachine()
    
    # Sanction rejection
    rejected = sm.transition_sanction_decision(ReimbursementStatus.PENDING_SANCTION.value, approve=False)
    assert rejected == ReimbursementStatus.REJECTED

    # Cannot forward if not in PENDING_PHC_REVIEW
    with pytest.raises(InvalidStateTransitionError):
        sm.transition_phc_review_forward(ReimbursementStatus.PENDING_ACCOUNTS_VERIFICATION.value)

    # Cannot verify if not in PENDING_ACCOUNTS_VERIFICATION
    with pytest.raises(InvalidStateTransitionError):
        sm.transition_accounts_verify(ReimbursementStatus.PENDING_PHC_REVIEW.value)

    # Cannot pay if not in APPROVED_FOR_PAYMENT
    with pytest.raises(InvalidStateTransitionError):
        sm.transition_payment_process(ReimbursementStatus.PENDING_SANCTION.value)


def test_claim_immutability_rule_br14():
    # Calling assert_can_modify raises ClaimImmutableError per BR-14
    with pytest.raises(ClaimImmutableError):
        ReimbursementStateMachine.assert_can_modify(ReimbursementStatus.PENDING_PHC_REVIEW.value)

    # Domain rule check
    eval_review = evaluate_claim_immutability(current_status=ReimbursementStatus.PENDING_ACCOUNTS_VERIFICATION)
    assert not eval_review.is_editable

    eval_rejected = evaluate_claim_immutability(current_status=ReimbursementStatus.REJECTED)
    assert not eval_rejected.is_editable


def test_claimant_eligibility_rule_br04():
    # Employees (faculty, staff) are eligible
    assert evaluate_claimant_eligibility(user_role="faculty").is_eligible
    assert evaluate_claimant_eligibility(user_role="staff").is_eligible
    assert evaluate_claimant_eligibility(user_role="phc_staff").is_eligible

    # Students are strictly ineligible per PHC-BR-04
    eval_student = evaluate_claimant_eligibility(user_role="student")
    assert not eval_student.is_eligible
    assert "Students are ineligible" in eval_student.reason


def test_prescription_requirement_rule_br05():
    # Prescription linked to same patient is valid
    eval_ok = evaluate_prescription_requirement(
        prescription_id=101,
        claimant_user_id=42,
        prescription_patient_user_id=42,
    )
    assert eval_ok.is_eligible

    # Missing prescription
    eval_missing = evaluate_prescription_requirement(
        prescription_id=None,
        claimant_user_id=42,
        prescription_patient_user_id=None,
    )
    assert not eval_missing.is_eligible

    # Prescription belongs to different user
    eval_mismatch = evaluate_prescription_requirement(
        prescription_id=101,
        claimant_user_id=42,
        prescription_patient_user_id=99,
    )
    assert not eval_mismatch.is_eligible


def test_submission_window_rule_br06():
    today = date.today()
    # Within 90 days
    eval_ok = evaluate_submission_window(expense_date=today - timedelta(days=30), current_date=today)
    assert eval_ok.is_eligible

    # Boundary: exactly 90 days
    eval_boundary = evaluate_submission_window(expense_date=today - timedelta(days=90), current_date=today)
    assert eval_boundary.is_eligible

    # Beyond 90 days
    eval_expired = evaluate_submission_window(expense_date=today - timedelta(days=91), current_date=today)
    assert not eval_expired.is_eligible


# --- Requisition State Machine & Inventory Rules ---

def test_requisition_state_machine_flow():
    sm = RequisitionStateMachine()
    
    # 1. Decision: Approve
    app = sm.transition_decision(RequisitionStatus.PENDING_APPROVAL.value, approve=True)
    assert app == RequisitionStatus.APPROVED

    # 2. Decision: Reject
    rej = sm.transition_decision(RequisitionStatus.PENDING_APPROVAL.value, approve=False)
    assert rej == RequisitionStatus.REJECTED

    # 3. Fulfill approved requisition
    ful = sm.transition_fulfill(RequisitionStatus.APPROVED.value)
    assert ful == RequisitionStatus.FULFILLED

    # Cannot fulfill pending or rejected requisition
    with pytest.raises(RequisitionNotApprovedError):
        sm.transition_fulfill(RequisitionStatus.PENDING_APPROVAL.value)

    with pytest.raises(RequisitionNotApprovedError):
        sm.transition_fulfill(RequisitionStatus.REJECTED.value)


def test_stock_threshold_rule_br07():
    # Stock strictly above threshold
    eval_normal = evaluate_stock_threshold(current_stock=50, reorder_threshold=20)
    assert not eval_normal.is_low_stock

    # Stock below threshold -> triggers low stock alert
    eval_low = evaluate_stock_threshold(current_stock=10, reorder_threshold=20)
    assert eval_low.is_low_stock
