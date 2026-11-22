"""Pure-Python domain tests for PSM: state machines, financial thresholds, and business rules."""
from decimal import Decimal

import pytest

from modules.psm.domain.state_machines import (
    DomainTransitionError,
    can_transition_indent,
    transition_discrepancy,
    transition_grn,
    transition_indent,
    transition_po,
)
from modules.psm.domain.threshold_policy import (
    DIRECT_PROCUREMENT_LIMIT,
    DIRECTOR_SANCTION_THRESHOLD,
    ProcurementMethod,
    determine_procurement_method,
    requires_director_approval,
)
from modules.psm.domain.validators import (
    ValidationError,
    VendorStatus,
    validate_indent_completeness,
    validate_rejection_reason,
    validate_vendor_verified_for_po,
)


def test_procurement_method_thresholds():
    """BR-PSM-008: Direct procurement <= 25k, Quotation <= 2.5L, Tender > 2.5L."""
    assert determine_procurement_method(Decimal("10000.00")) == ProcurementMethod.DIRECT
    assert determine_procurement_method(DIRECT_PROCUREMENT_LIMIT) == ProcurementMethod.DIRECT

    assert determine_procurement_method(Decimal("25000.01")) == ProcurementMethod.QUOTATION
    assert determine_procurement_method(Decimal("150000.00")) == ProcurementMethod.QUOTATION
    assert determine_procurement_method(DIRECTOR_SANCTION_THRESHOLD) == ProcurementMethod.QUOTATION

    assert determine_procurement_method(Decimal("250000.01")) == ProcurementMethod.TENDER
    assert determine_procurement_method(Decimal("1000000.00")) == ProcurementMethod.TENDER


def test_director_approval_policy():
    """BR-PSM-010: High-value procurement requires Director sanction."""
    assert not requires_director_approval(Decimal("249999.99"))
    assert requires_director_approval(Decimal("250000.00"))
    assert requires_director_approval(Decimal("500000.00"))


def test_indent_state_transitions():
    """Tests valid lifecycle transitions for indents."""
    assert can_transition_indent("DRAFT", "SUBMIT", "requestor")
    assert transition_indent("DRAFT", "SUBMIT", "requestor") == "SUBMITTED"

    assert transition_indent("SUBMITTED", "DEPT_VERIFY", "dept_admin") == "PENDING_DEPT_APPROVAL"
    assert transition_indent("PENDING_DEPT_APPROVAL", "HOD_APPROVE_LOW", "hod") == "PENDING_PS_REVIEW"
    assert transition_indent("PENDING_PS_REVIEW", "PS_APPROVE_STANDARD", "ps_admin") == "APPROVED"
    assert transition_indent("APPROVED", "ISSUE_PO", "purchase_officer") == "FULFILLED"


def test_indent_director_escalation_path():
    """Tests director escalation for high-value indents."""
    assert (
        transition_indent("PENDING_PS_REVIEW", "PS_ESCALATE_HIGH_VALUE", "ps_admin")
        == "PENDING_DIRECTOR_APPROVAL"
    )
    assert transition_indent("PENDING_DIRECTOR_APPROVAL", "DIRECTOR_APPROVE", "director") == "APPROVED"


def test_illegal_indent_transition_raises():
    """Ensures unauthorized or invalid transitions raise DomainTransitionError."""
    with pytest.raises(DomainTransitionError):
        transition_indent("DRAFT", "DIRECTOR_APPROVE", "director")

    with pytest.raises(DomainTransitionError):
        transition_indent("SUBMITTED", "HOD_APPROVE_LOW", "requestor")


def test_po_transitions():
    """Tests PO issuing, delivery recording, and cancellation."""
    assert transition_po("DRAFT", "ISSUE", "purchase_officer") == "ISSUED"
    assert transition_po("ISSUED", "RECORD_DELIVERY_PARTIAL", "store_keeper") == "PARTIALLY_DELIVERED"
    assert transition_po("PARTIALLY_DELIVERED", "RECORD_DELIVERY_COMPLETE", "store_keeper") == "COMPLETED"
    assert transition_po("ISSUED", "CANCEL", "purchase_officer") == "CANCELLED"

    with pytest.raises(DomainTransitionError):
        transition_po("COMPLETED", "CANCEL", "purchase_officer")


def test_grn_transitions():
    """Tests GRN inspection and acceptance lifecycle."""
    assert transition_grn("INSPECTION_PENDING", "ACCEPT_ALL", "store_keeper") == "ACCEPTED"
    assert transition_grn("INSPECTION_PENDING", "FLAG_DISCREPANCY", "store_keeper") == "DISCREPANT"
    assert transition_grn("ACCEPTED", "INDENTOR_CONFIRM", "requestor") == "CLOSED"


def test_discrepancy_transitions():
    """Tests resolution of shipment discrepancies."""
    assert transition_discrepancy("OPEN_HOLD_PAYMENT", "RESOLVE", "purchase_officer") == "RESOLVED"
    with pytest.raises(DomainTransitionError):
        transition_discrepancy("RESOLVED", "RESOLVE", "purchase_officer")


def test_validate_indent_completeness():
    """BR-PSM-001: Completeness verification."""
    with pytest.raises(ValidationError, match="title cannot be empty"):
        validate_indent_completeness("", "Academic purpose", [{"quantity_requested": 1, "estimated_unit_cost": 100}])

    with pytest.raises(ValidationError, match="justification cannot be empty"):
        validate_indent_completeness("Title", "", [{"quantity_requested": 1, "estimated_unit_cost": 100}])

    with pytest.raises(ValidationError, match="at least one item line"):
        validate_indent_completeness("Title", "Purpose", [])

    with pytest.raises(ValidationError, match="positive quantity"):
        validate_indent_completeness("Title", "Purpose", [{"quantity_requested": 0, "estimated_unit_cost": 100}])

    with pytest.raises(ValidationError, match="negative unit cost"):
        validate_indent_completeness("Title", "Purpose", [{"quantity_requested": 5, "estimated_unit_cost": -10}])


def test_validate_rejection_reason():
    """BR-PSM-005: Rejection justification is mandatory."""
    with pytest.raises(ValidationError, match="Rejection justification cannot be empty"):
        validate_rejection_reason("")

    validate_rejection_reason("Insufficient departmental budget allocation.")


def test_validate_vendor_verified_for_po():
    """BR-PSM-012 / DEF-PSM-005: PO issuance to unverified vendor strictly prevented."""
    with pytest.raises(ValidationError, match="Only VERIFIED vendors"):
        validate_vendor_verified_for_po(VendorStatus.DRAFT, "Acme Corp")

    with pytest.raises(ValidationError, match="Only VERIFIED vendors"):
        validate_vendor_verified_for_po(VendorStatus.SUBMITTED, "Acme Corp")

    with pytest.raises(ValidationError, match="Only VERIFIED vendors"):
        validate_vendor_verified_for_po(VendorStatus.BLACKLISTED, "Acme Corp")

    # Should not raise for VERIFIED
    validate_vendor_verified_for_po(VendorStatus.VERIFIED, "Acme Corp")
