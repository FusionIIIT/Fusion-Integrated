"""Pure-Python domain unit tests for HR-EIS."""
from datetime import date
from decimal import Decimal
import pytest

from modules.hreis.domain.appraisal import (
    AppraisalStatus,
    validate_appraisal_finalization,
    validate_appraisal_submission,
    validate_appraisal_window,
)
from modules.hreis.domain.exceptions import DomainValidationError
from modules.hreis.domain.claims import (
    ClaimType,
    validate_cpda_submission,
    validate_financial_settlement,
    validate_ltc_submission,
)
from modules.hreis.domain.leave import (
    DEFAULT_LEAVE_QUOTAS,
    LeaveType,
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


def test_leave_validation_insufficient_balance():
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


def test_leave_validation_sabbatical_only_for_faculty():
    balances = {"sabbatical": 365.0}
    with pytest.raises(DomainValidationError, match="faculty"):
        validate_leave_submission(
            leave_type="sabbatical",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 12, 1),
            duration_days=180.0,
            justification="Research collaboration",
            category="staff",
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


def test_appraisal_immutability():
    with pytest.raises(DomainValidationError, match="cannot be modified"):
        validate_appraisal_submission("2025-2026", {"achievements": "test"}, AppraisalStatus.FINALIZED.value)


def test_ltc_validation():
    validate_ltc_submission(
        request_type=ClaimType.ADVANCE.value,
        block_year="2026-2029",
        travel_from="Jabalpur",
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


def test_cpda_validation():
    validate_cpda_submission(
        request_type=ClaimType.REIMBURSEMENT.value,
        purpose="IEEE International Conference Registration",
        amount=Decimal("25000.00"),
        available_balance=Decimal("100000.00"),
        supporting_documents=["receipt_123.pdf"],
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


def test_financial_settlement_validation():
    validate_financial_settlement(passed_amount=Decimal("24500.00"), reference_id="VOUCHER-2026-001")

    with pytest.raises(DomainValidationError, match="positive"):
        validate_financial_settlement(passed_amount=Decimal("0.00"), reference_id="VOUCHER-2026-001")


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
