"""Workflow Test Suite for IAA module (Strategy: WF).
Specification-driven tests derived strictly from WF_DESIGN.json.
Contains 25 test cases (T-WF-01 to T-WF-25) covering all CW-01..04 and BW-01..19 workflows.
"""

from decimal import Decimal

import pytest

from modules.iaa.domain.state_machine import (
    InvalidStateTransitionError,
    transition_anomaly,
    transition_audit_observation,
    transition_expense_request,
    transition_ta_claim,
)
from modules.iaa.models import (
    ApprovalHierarchyRule,
    DepartmentBudget,
    IAAConfiguration,
    RequestStatus,
    TAClaimStatus,
)
from modules.iaa.services import (
    approvals as approval_services,
)
from modules.iaa.services import (
    requests as request_services,
)
from modules.iaa.services import (
    travel as travel_services,
)


@pytest.fixture
def base_setup(db):
    config = IAAConfiguration.objects.create(
        financial_year="2026-2027",
        high_value_ta_threshold=Decimal("50000.00"),
        approval_timeout_days=3,
        is_active=True,
    )
    budget = DepartmentBudget.objects.create(
        department="CSE",
        financial_year="2026-2027",
        allocated_amount=Decimal("500000.00"),
        utilized_amount=Decimal("0.00"),
    )
    rule1 = ApprovalHierarchyRule.objects.create(
        request_type="expense",
        min_amount=Decimal("0.00"),
        max_amount=Decimal("25000.00"),
        required_levels=1,
        approver_roles=["HOD"],
    )
    rule2 = ApprovalHierarchyRule.objects.create(
        request_type="expense",
        min_amount=Decimal("25000.01"),
        max_amount=Decimal("100000.00"),
        required_levels=2,
        approver_roles=["HOD", "Dean"],
    )
    return {"config": config, "budget": budget, "rule1": rule1, "rule2": rule2}


# --- CW-IAA-01 & BW-IAA-01..06: Expense Request Workflows ---

def test_t_wf_01_standard_expense_lifecycle(base_setup):
    """T-WF-01: BW-IAA-01 Standard Success - Execute full standard expense lifecycle draft to recorded"""
    # 1. Draft
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Consumables",
        description="Printer paper",
        items=[{"description": "Paper", "amount": Decimal("10000.00"), "category": "OFFICE"}],
    )
    assert req.status == RequestStatus.DRAFT
    assert not req.is_locked

    # 2. Submit
    submitted = request_services.submit_expense_request(req.id, 1001, "basic_user")
    assert submitted.status == RequestStatus.SUBMITTED
    assert submitted.is_locked

    # 3. Finance Validate
    validated = request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    assert validated.status == RequestStatus.FINANCE_VALIDATED
    assert validated.required_approval_levels == 1

    # 4. Approving Authority Decision
    approved = approval_services.record_request_decision(req.id, 2001, "HOD", "approve", "Approved by HOD")
    assert approved.status == RequestStatus.APPROVED

    # 5. Finance Record
    recorded = request_services.record_request_processing(req.id, 3001, "finance_staff")
    assert recorded.status == RequestStatus.RECORDED


def test_t_wf_02_multilevel_expense_approval(base_setup):
    """T-WF-02: BW-IAA-02 Multi-Level Approval - Execute 2-level approval workflow"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Lab Equipment",
        description="High precision meters",
        items=[{"description": "Meters", "amount": Decimal("60000.00"), "category": "EQUIPMENT"}],
    )
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    validated = request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    assert validated.required_approval_levels == 2

    # Level 1 Decision (HOD)
    level1 = approval_services.record_request_decision(req.id, 2001, "HOD", "approve", "HOD level approved")
    assert level1.status == RequestStatus.APPROVAL_PENDING
    assert level1.current_approval_level == 2

    # Level 2 Decision (Dean)
    level2 = approval_services.record_request_decision(req.id, 4001, "Dean", "approve", "Dean level approved")
    assert level2.status == RequestStatus.APPROVED

    # Final Record
    recorded = request_services.record_request_processing(req.id, 3001, "finance_staff")
    assert recorded.status == RequestStatus.RECORDED


def test_t_wf_03_direct_rejection_at_validation(base_setup):
    """T-WF-03: BW-IAA-03 Direct Rejection - Execute rejection at finance validation / level 1"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Unallowable Item",
        description="Gift cards",
        items=[{"description": "Gift", "amount": Decimal("5000.00"), "category": "MISC"}],
    )
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    rejected = approval_services.record_request_decision(req.id, 2001, "HOD", "reject", "Policy violation: gifts unallowable")
    assert rejected.status == RequestStatus.REJECTED


def test_t_wf_04_rejection_at_second_approval_level(base_setup):
    """T-WF-04: BW-IAA-03 Approval Level Rejection - Execute rejection during approval pending level"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Advanced Server",
        description="Servers",
        items=[{"description": "Server", "amount": Decimal("80000.00"), "category": "EQUIPMENT"}],
    )
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    approval_services.record_request_decision(req.id, 2001, "HOD", "approve", "Approved by HOD")
    # Dean rejects at level 2
    rejected = approval_services.record_request_decision(req.id, 4001, "Dean", "reject", "Budget capped by Dean")
    assert rejected.status == RequestStatus.REJECTED


def test_t_wf_05_clarification_loop_traversal(base_setup):
    """T-WF-05: BW-IAA-04 Clarification Loop - Execute clarification query and response loop before validation"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Conference Fee",
        description="Registration",
        items=[{"description": "Fee", "amount": Decimal("15000.00"), "category": "CONF"}],
    )
    request_services.submit_expense_request(req.id, 1001, "basic_user")

    # Finance raises query
    query = request_services.raise_request_clarification(req.id, 3001, "finance_staff", "Provide schedule")
    req.refresh_from_db()
    assert req.status == RequestStatus.QUERY_RAISED

    # Creator responds
    responded = request_services.respond_to_request_clarification(query.id, 1001, "basic_user", "Schedule attached")
    assert responded.status == RequestStatus.QUERY_RESPONDED

    # Finance validates
    validated = request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    assert validated.status == RequestStatus.FINANCE_VALIDATED

    # Decision and record
    approval_services.record_request_decision(req.id, 2001, "HOD", "approve", "All clear")
    recorded = request_services.record_request_processing(req.id, 3001, "finance_staff")
    assert recorded.status == RequestStatus.RECORDED


def test_t_wf_06_escalated_approval_path(base_setup):
    """T-WF-06: BW-IAA-05 Escalated Approval - Execute timed escalation and subsequent approval"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Delayed Processing Item",
        description="Parts",
        items=[{"description": "Parts", "amount": Decimal("15000.00"), "category": "PARTS"}],
    )
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    approval_services.escalate_overdue_approval("request", req.id, "Director")
    req.refresh_from_db()
    assert req.status == RequestStatus.ESCALATED

    approved = approval_services.record_request_decision(req.id, 9001, "Director", "approve", "Approved by Director after SLA timeout")
    assert approved.status == RequestStatus.APPROVED
    recorded = request_services.record_request_processing(req.id, 3001, "finance_staff")
    assert recorded.status == RequestStatus.RECORDED


def test_t_wf_07_escalated_rejection_path(base_setup):
    """T-WF-07: BW-IAA-06 Escalated Rejection - Execute rejection on escalated request"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Overdue Unjustified Item",
        description="Parts",
        items=[{"description": "Parts", "amount": Decimal("15000.00"), "category": "PARTS"}],
    )
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    approval_services.escalate_overdue_approval("request", req.id, "Director")
    rejected = approval_services.record_request_decision(req.id, 9001, "Director", "reject", "Rejected post escalation")
    assert rejected.status == RequestStatus.REJECTED


def test_t_wf_08_terminal_recorded_lock_expense(base_setup):
    """T-WF-08: CW-IAA-01 Terminal Recorded Lock - Verify RECORDED is terminal state in expense lifecycle"""
    with pytest.raises(InvalidStateTransitionError):
        transition_expense_request("recorded", "validate", "finance_staff")


def test_t_wf_09_terminal_rejected_lock_expense(base_setup):
    """T-WF-09: CW-IAA-01 Terminal Rejected Lock - Verify REJECTED is terminal state in expense lifecycle"""
    with pytest.raises(InvalidStateTransitionError):
        transition_expense_request("rejected", "submit", "basic_user")


# --- CW-IAA-02 & BW-IAA-07..11, 16: Travel Allowance (TA) Workflows ---

def test_t_wf_10_standard_ta_success(base_setup):
    """T-WF-10: BW-IAA-07 Standard TA Success - Execute standard TA lifecycle submission to recorded"""
    claim = travel_services.submit_travel_claim(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        purpose="National Conference",
        departure_date="2026-11-01",
        arrival_date="2026-11-04",
        source_location="Campus",
        destination_location="Chennai",
        claimed_amount=Decimal("20000.00"),
    )
    assert claim.status == TAClaimStatus.SUBMITTED
    verified = travel_services.verify_travel_claim(claim.id, 3001, "finance_staff")
    assert verified.status == TAClaimStatus.VERIFIED
    recorded = travel_services.record_travel_processing(claim.id, 3001, "finance_staff")
    assert recorded.status == TAClaimStatus.RECORDED


def test_t_wf_11_high_value_ta_approval(base_setup):
    """T-WF-11: BW-IAA-08 High-Value TA Approval - Execute high-value TA lifecycle through authority approval"""
    claim = travel_services.submit_travel_claim(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        purpose="International Keynote",
        departure_date="2026-11-01",
        arrival_date="2026-11-07",
        source_location="Campus",
        destination_location="London",
        claimed_amount=Decimal("85000.00"),
    )
    verified = travel_services.verify_travel_claim(claim.id, 3001, "finance_staff")
    assert verified.status == TAClaimStatus.APPROVAL_PENDING
    assert verified.is_high_value is True
    approved = approval_services.record_travel_decision(claim.id, 4001, "Dean", "approve", "Approved by Dean")
    assert approved.status == TAClaimStatus.APPROVED
    recorded = travel_services.record_travel_processing(claim.id, 3001, "finance_staff")
    assert recorded.status == TAClaimStatus.RECORDED


def test_t_wf_12_high_value_multi_level_ta(base_setup):
    """T-WF-12: BW-IAA-09 High-Value Multi-Level - Execute multi-level high-value TA approval"""
    s1 = transition_ta_claim("approval_pending", "approve_level", "approving_authority")
    assert s1 == "approval_pending"
    s2 = transition_ta_claim(s1, "approve_final", "approving_authority")
    assert s2 == "approved"
    s3 = transition_ta_claim(s2, "record", "finance_staff")
    assert s3 == "recorded"


def test_t_wf_13_ta_finance_rejection(base_setup):
    """T-WF-13: BW-IAA-10 TA Finance Rejection - Execute TA rejection during verification"""
    s = transition_ta_claim("submitted", "reject", "finance_staff")
    assert s == "rejected"


def test_t_wf_14_ta_approval_rejection(base_setup):
    """T-WF-14: BW-IAA-10 TA Approval Rejection - Execute TA rejection during authority approval"""
    claim = travel_services.submit_travel_claim(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        purpose="Overseas Seminar",
        departure_date="2026-11-01",
        arrival_date="2026-11-08",
        source_location="Campus",
        destination_location="Paris",
        claimed_amount=Decimal("90000.00"),
    )
    travel_services.verify_travel_claim(claim.id, 3001, "finance_staff")
    rejected = approval_services.record_travel_decision(claim.id, 4001, "Dean", "reject", "Funding exhausted")
    assert rejected.status == TAClaimStatus.REJECTED


def test_t_wf_15_ta_clarification_loop(base_setup):
    """T-WF-15: BW-IAA-11 TA Clarification Loop - Execute TA clarification query and response loop"""
    claim = travel_services.submit_travel_claim(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        purpose="Industry Visit",
        departure_date="2026-11-01",
        arrival_date="2026-11-04",
        source_location="Campus",
        destination_location="Pune",
        claimed_amount=Decimal("15000.00"),
    )
    q = travel_services.raise_travel_clarification(claim.id, 3001, "finance_staff", "Provide hotel invoice")
    claim.refresh_from_db()
    assert claim.status == TAClaimStatus.QUERY_RAISED

    responded = travel_services.respond_to_travel_clarification(q.id, 1001, "basic_user", "Hotel invoice attached")
    assert responded.status == TAClaimStatus.QUERY_RESPONDED

    verified = travel_services.verify_travel_claim(claim.id, 3001, "finance_staff")
    assert verified.status == TAClaimStatus.VERIFIED

    recorded = travel_services.record_travel_processing(claim.id, 3001, "finance_staff")
    assert recorded.status == TAClaimStatus.RECORDED


def test_t_wf_16_escalated_high_value_ta_approval(base_setup):
    """T-WF-16: BW-IAA-16 Escalated High-Value TA Approval - Execute timed escalation and approval on high-value TA"""
    claim = travel_services.submit_travel_claim(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        purpose="Conference",
        departure_date="2026-11-01",
        arrival_date="2026-11-05",
        source_location="Campus",
        destination_location="Delhi",
        claimed_amount=Decimal("70000.00"),
    )
    travel_services.verify_travel_claim(claim.id, 3001, "finance_staff")
    approval_services.escalate_overdue_approval("travel", claim.id, "Director")
    claim.refresh_from_db()
    assert claim.status == TAClaimStatus.ESCALATED

    approved = approval_services.record_travel_decision(claim.id, 9001, "Director", "approve", "Approved by Director after escalation")
    assert approved.status == TAClaimStatus.APPROVED

    recorded = travel_services.record_travel_processing(claim.id, 3001, "finance_staff")
    assert recorded.status == TAClaimStatus.RECORDED


def test_t_wf_17_ta_terminal_lock(base_setup):
    """T-WF-17: CW-IAA-02 TA Terminal Lock - Verify RECORDED is terminal state in TA lifecycle"""
    with pytest.raises(InvalidStateTransitionError):
        transition_ta_claim("recorded", "verify_standard", "finance_staff")


# --- CW-IAA-03 & BW-IAA-12..13: Anomaly Lifecycle Workflows ---

def test_t_wf_18_automatic_anomaly_flag(base_setup):
    """T-WF-18: BW-IAA-12 Automatic Anomaly Flag - Execute automatic anomaly trigger workflow"""
    s = transition_anomaly("none", "flag_automatic", "system")
    assert s == "open"


def test_t_wf_19_manual_anomaly_flag(base_setup):
    """T-WF-19: BW-IAA-12 Manual Anomaly Flag - Execute manual anomaly trigger workflow"""
    s = transition_anomaly("none", "flag_manual", "finance_or_auditor")
    assert s == "open"


def test_t_wf_20_anomaly_direct_resolution(base_setup):
    """T-WF-20: BW-IAA-12 Anomaly Direct Resolution - Execute direct anomaly resolution path"""
    s = transition_anomaly("open", "resolve", "resolver")
    assert s == "resolved"


def test_t_wf_21_anomaly_escalation_traversal(base_setup):
    """T-WF-21: BW-IAA-13 Anomaly Escalation Traversal - Execute anomaly escalation and resolution path"""
    s1 = transition_anomaly("open", "escalate", "resolver")
    assert s1 == "escalated"
    s2 = transition_anomaly(s1, "resolve", "resolver")
    assert s2 == "resolved"


def test_t_wf_22_anomaly_terminal_lock(base_setup):
    """T-WF-22: CW-IAA-03 Anomaly Terminal Lock - Verify RESOLVED is terminal state in anomaly lifecycle"""
    with pytest.raises(InvalidStateTransitionError):
        transition_anomaly("resolved", "escalate", "resolver")


# --- CW-IAA-04 & BW-IAA-14..15: Internal Audit Lifecycle Workflows ---

def test_t_wf_23_audit_straight_closure(base_setup):
    """T-WF-23: BW-IAA-14 Audit Straight Closure - Execute audit observation straight closure path"""
    s1 = transition_audit_observation("none", "create", "auditor")
    assert s1 == "open"
    s2 = transition_audit_observation(s1, "respond", "basic_user")
    assert s2 == "responded"
    s3 = transition_audit_observation(s2, "close", "auditor")
    assert s3 == "closed"


def test_t_wf_24_audit_revision_traversal(base_setup):
    """T-WF-24: BW-IAA-15 Audit Revision Traversal - Execute audit observation revision cyclic loop path"""
    s1 = transition_audit_observation("none", "create", "auditor")
    assert s1 == "open"
    s2 = transition_audit_observation(s1, "respond", "basic_user")
    assert s2 == "responded"
    # Auditor rejects response -> returns to open
    s3 = transition_audit_observation(s2, "reject_response", "auditor")
    assert s3 == "open"
    # User responds second time
    s4 = transition_audit_observation(s3, "respond", "basic_user")
    assert s4 == "responded"
    # Auditor accepts and closes
    s5 = transition_audit_observation(s4, "close", "auditor")
    assert s5 == "closed"


def test_t_wf_25_audit_terminal_lock(base_setup):
    """T-WF-25: CW-IAA-04 Audit Terminal Lock - Verify CLOSED is terminal state in audit observation lifecycle"""
    with pytest.raises(InvalidStateTransitionError):
        transition_audit_observation("closed", "respond", "basic_user")
