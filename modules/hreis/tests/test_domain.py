"""Pure-Python domain unit tests for HR-EIS."""

from datetime import date
from decimal import Decimal

import pytest

from modules.hreis.domain.appraisal import (
    AppraisalStatus,
    validate_appraisal_finalization,
    validate_appraisal_submission,
    validate_appraisal_window,
    validate_reviewer_assignment,
)
from modules.hreis.domain.claims import (
    ClaimType,
    validate_cpda_submission,
    validate_financial_settlement,
    validate_ltc_submission,
)
from modules.hreis.domain.exceptions import DomainValidationError
from modules.hreis.domain.leave import (
    calculate_new_balance,
    validate_leave_submission,
)
from modules.hreis.domain.workflow import DecisionOutcome, get_next_authority, validate_decision


def test_leave_validation_valid():
    balances = {"casual": 8.0, "medical": 15.0}
    validate_leave_submission(
        leave_type="casual",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 3),
        duration_days=3.0,
        justification="Personal family event",
        category="faculty",
        current_balances=balances,
    )


def test_leave_validation_errors():
    balances = {"casual": 2.0}
    with pytest.raises(DomainValidationError, match="Insufficient leave balance"):
        validate_leave_submission(
            leave_type="casual",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 5),
            duration_days=5.0,
            justification="Vacation trip",
            category="staff",
            current_balances=balances,
        )

    with pytest.raises(DomainValidationError, match="faculty"):
        validate_leave_submission(
            leave_type="sabbatical",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 12, 1),
            duration_days=180.0,
            justification="Research collaboration",
            category="staff",
            current_balances={"sabbatical": 365.0},
        )

    with pytest.raises(DomainValidationError, match="greater than zero"):
        validate_leave_submission(
            leave_type="casual",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 3),
            duration_days=0.0,
            justification="Trip",
            category="faculty",
            current_balances=balances,
        )

    with pytest.raises(DomainValidationError, match="cannot precede"):
        validate_leave_submission(
            leave_type="casual",
            start_date=date(2026, 3, 5),
            end_date=date(2026, 3, 1),
            duration_days=2.0,
            justification="Trip",
            category="faculty",
            current_balances=balances,
        )

    with pytest.raises(DomainValidationError, match="justification is required"):
        validate_leave_submission(
            leave_type="casual",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 2),
            duration_days=1.0,
            justification="",
            category="faculty",
            current_balances=balances,
        )

    with pytest.raises(DomainValidationError, match="Invalid leave type"):
        validate_leave_submission(
            leave_type="unsupported",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 2),
            duration_days=1.0,
            justification="Trip",
            category="faculty",
            current_balances=balances,
        )


def test_calculate_new_balance():
    balances = {"casual": 8.0, "medical": 15.0}
    updated = calculate_new_balance(balances, "casual", 3.0)
    assert updated["casual"] == 5.0
    assert updated["medical"] == 15.0


def test_appraisal_window_enforcement():
    cfg = {"active": True, "start_date": "2026-01-01", "end_date": "2026-06-30"}
    validate_appraisal_window(date(2026, 3, 15), cfg)

    with pytest.raises(DomainValidationError, match="closed"):
        validate_appraisal_window(date(2026, 3, 15), {"active": False})

    with pytest.raises(DomainValidationError, match="between"):
        validate_appraisal_window(date(2026, 7, 1), cfg)


def test_appraisal_validation_errors():
    with pytest.raises(DomainValidationError, match="cannot be modified"):
        validate_appraisal_submission(
            "2025-2026", {"achievements": "test"}, AppraisalStatus.FINALIZED.value
        )

    with pytest.raises(DomainValidationError, match="Academic year"):
        validate_appraisal_submission("", {"achievements": "test"}, AppraisalStatus.SUBMITTED.value)

    with pytest.raises(DomainValidationError, match="empty"):
        validate_appraisal_submission("2025-2026", {}, AppraisalStatus.SUBMITTED.value)

    with pytest.raises(DomainValidationError, match="Cannot assign"):
        validate_reviewer_assignment(AppraisalStatus.FINALIZED.value, [401])

    with pytest.raises(DomainValidationError, match="At least one"):
        validate_reviewer_assignment(AppraisalStatus.SUBMITTED.value, [])

    with pytest.raises(DomainValidationError, match="immutable"):
        validate_appraisal_finalization(AppraisalStatus.FINALIZED.value, 8.5, "Good")

    with pytest.raises(DomainValidationError, match="between 0 and 100"):
        validate_appraisal_finalization(AppraisalStatus.UNDER_REVIEW.value, 105.0, "Good")

    with pytest.raises(DomainValidationError, match="Final remarks"):
        validate_appraisal_finalization(AppraisalStatus.UNDER_REVIEW.value, 8.5, "")


def test_ltc_validation():
    validate_ltc_submission(
        request_type=ClaimType.ADVANCE.value,
        block_year="2026-2029",
        travel_from="Jabalpur",
        travel_to="New Delhi",
        estimated_amount=Decimal("15000.00"),
        claimed_amount=None,
    )

    with pytest.raises(DomainValidationError, match="Invalid LTC request type"):
        validate_ltc_submission(
            request_type="invalid",
            block_year="2026-2029",
            travel_from="Jabalpur",
            travel_to="New Delhi",
            estimated_amount=Decimal("15000.00"),
            claimed_amount=None,
        )

    with pytest.raises(DomainValidationError, match="block year is required"):
        validate_ltc_submission(
            request_type=ClaimType.ADVANCE.value,
            block_year="",
            travel_from="Jabalpur",
            travel_to="New Delhi",
            estimated_amount=Decimal("15000.00"),
            claimed_amount=None,
        )

    with pytest.raises(DomainValidationError, match="origin and destination"):
        validate_ltc_submission(
            request_type=ClaimType.ADVANCE.value,
            block_year="2026-2029",
            travel_from="",
            travel_to="New Delhi",
            estimated_amount=Decimal("15000.00"),
            claimed_amount=None,
        )

    with pytest.raises(DomainValidationError, match="greater than zero"):
        validate_ltc_submission(
            request_type=ClaimType.ADVANCE.value,
            block_year="2026-2029",
            travel_from="Jabalpur",
            travel_to="New Delhi",
            estimated_amount=Decimal("0.00"),
            claimed_amount=None,
        )

    with pytest.raises(DomainValidationError, match="Claimed amount is required"):
        validate_ltc_submission(
            request_type=ClaimType.REIMBURSEMENT.value,
            block_year="2026-2029",
            travel_from="Jabalpur",
            travel_to="Delhi",
            estimated_amount=Decimal("15000.00"),
            claimed_amount=Decimal("0.00"),
        )


def test_cpda_validation():
    validate_cpda_submission(
        request_type=ClaimType.REIMBURSEMENT.value,
        purpose="IEEE International Conference Registration",
        amount=Decimal("25000.00"),
        available_balance=Decimal("100000.00"),
        supporting_documents=["receipt_123.pdf"],
    )

    with pytest.raises(DomainValidationError, match="Invalid CPDA request type"):
        validate_cpda_submission(
            request_type="bad_type",
            purpose="Books",
            amount=Decimal("2000.00"),
            available_balance=Decimal("100000.00"),
            supporting_documents=["receipt.pdf"],
        )

    with pytest.raises(DomainValidationError, match="Supporting documents are required"):
        validate_cpda_submission(
            request_type=ClaimType.REIMBURSEMENT.value,
            purpose="Conference Registration",
            amount=Decimal("25000.00"),
            available_balance=Decimal("100000.00"),
            supporting_documents=[],
        )

    with pytest.raises(DomainValidationError, match="exceeds available CPDA balance"):
        validate_cpda_submission(
            request_type=ClaimType.REIMBURSEMENT.value,
            purpose="Hardware",
            amount=Decimal("150000.00"),
            available_balance=Decimal("100000.00"),
            supporting_documents=["bill.pdf"],
        )

    with pytest.raises(DomainValidationError, match="greater than zero"):
        validate_cpda_submission(
            request_type=ClaimType.ADVANCE.value,
            purpose="Books",
            amount=Decimal("0.00"),
            available_balance=Decimal("50000.00"),
            supporting_documents=[],
        )

    with pytest.raises(DomainValidationError, match="Purpose is required"):
        validate_cpda_submission(
            request_type=ClaimType.ADVANCE.value,
            purpose="",
            amount=Decimal("5000.00"),
            available_balance=Decimal("50000.00"),
            supporting_documents=[],
        )


def test_financial_settlement_validation():
    validate_financial_settlement(
        passed_amount=Decimal("24500.00"), reference_id="VOUCHER-2026-001"
    )

    with pytest.raises(DomainValidationError, match="positive"):
        validate_financial_settlement(
            passed_amount=Decimal("0.00"), reference_id="VOUCHER-2026-001"
        )

    with pytest.raises(DomainValidationError, match="reference"):
        validate_financial_settlement(
            passed_amount=Decimal("24500.00"), reference_id=""
        )


def test_workflow_hierarchy_and_decisions():
    hierarchy = {"faculty": ["hod", "director"], "staff": ["registrar"]}
    assert get_next_authority("", "faculty", hierarchy) == "hod"
    assert get_next_authority("hod", "faculty", hierarchy) == "director"
    assert get_next_authority("director", "faculty", hierarchy) is None

    # Forwarding at final authority must fail
    with pytest.raises(DomainValidationError, match="final authority"):
        validate_decision(
            outcome=DecisionOutcome.FORWARDED.value,
            current_status="pending",
            remarks="Forwarding",
            can_forward=False,
        )

    # Rejection without remarks must fail
    with pytest.raises(DomainValidationError, match="Remarks are required"):
        validate_decision(
            outcome=DecisionOutcome.REJECTED.value,
            current_status="pending",
            remarks="",
            can_forward=True,
        )

    with pytest.raises(DomainValidationError, match="Invalid decision outcome"):
        validate_decision(
            outcome="unknown_action",
            current_status="pending",
            remarks="test",
            can_forward=True,
        )

    with pytest.raises(DomainValidationError, match="already in terminal state"):
        validate_decision(
            outcome=DecisionOutcome.APPROVED.value,
            current_status="approved",
            remarks="test",
            can_forward=True,
        )
