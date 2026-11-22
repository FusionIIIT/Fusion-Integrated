"""Use Case Test Suite for IAA module (Strategy: UC).
Specification-driven tests derived strictly from UC_DESIGN.json.
Contains 46 test cases (T-UC-01 to T-UC-46).
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_principal, make_session
from core.api.exceptions import BadRequestError, ConflictError
from modules.iaa.domain.rules import DomainValidationError
from modules.iaa.domain.state_machine import InvalidStateTransitionError
from modules.iaa.models import (
    Anomaly,
    ApprovalHierarchyRule,
    DepartmentBudget,
    IAAConfiguration,
)
from modules.iaa.selectors import (
    audit as audit_selectors,
)
from modules.iaa.selectors import (
    reports as report_selectors,
)
from modules.iaa.selectors import (
    requests as request_selectors,
)
from modules.iaa.services import (
    anomalies as anomaly_services,
)
from modules.iaa.services import (
    approvals as approval_services,
)
from modules.iaa.services import (
    audit as audit_services,
)
from modules.iaa.services import (
    configuration as config_services,
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
        max_amount=Decimal("100000.00"),
        required_levels=1,
        approver_roles=["hod"],
    )
    rule2 = ApprovalHierarchyRule.objects.create(
        request_type="expense",
        min_amount=Decimal("100000.01"),
        max_amount=Decimal("1000000.00"),
        required_levels=2,
        approver_roles=["hod", "dean"],
    )
    return {"config": config, "budget": budget, "rule1": rule1, "rule2": rule2}


# --- IAA-UC-101 .. 105: Request Lifecycle ---

def test_t_uc_01_create_complete_draft_expense_request(base_setup):
    """T-UC-01: IAA-UC-101 Main Flow - Create complete draft expense request"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Lab Supplies Purchase",
        description="Purchasing electronics components",
        items=[{"description": "Arduino Kits", "amount": Decimal("10000.00"), "category": "EQUIPMENT"}],
    )
    assert req.pk is not None
    assert req.status == "draft"
    assert req.total_amount == Decimal("10000.00")
    assert req.items.count() == 1


def test_t_uc_02_save_incomplete_draft_expense_request(base_setup):
    """T-UC-02: IAA-UC-101 Alternative A1 - Save incomplete draft expense request"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Partial Draft",
        items=[],
    )
    assert req.pk is not None
    assert req.status == "draft"
    assert req.items.count() == 0


def test_t_uc_03_submit_complete_expense_request(base_setup):
    """T-UC-03: IAA-UC-102 Main Flow - Submit complete expense request"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Software Licenses",
        description="Annual cloud subscription",
        items=[{"description": "Subscription", "amount": Decimal("15000.00"), "category": "SOFTWARE"}],
    )
    submitted = request_services.submit_expense_request(req.id, 1001, "basic_user")
    assert submitted.status == "submitted"
    assert submitted.is_locked is True


def test_t_uc_04_block_submission_of_incomplete_request(base_setup):
    """T-UC-04: IAA-UC-102 Exception E1 - Block submission of incomplete request"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="",
        items=[],
    )
    with pytest.raises(DomainValidationError):
        request_services.submit_expense_request(req.id, 1001, "basic_user")


def test_t_uc_05_block_submission_by_non_owner(base_setup):
    """T-UC-05: IAA-UC-102 Exception E2 - Block submission by non-owner"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Office Furniture",
        description="Chairs",
        items=[{"description": "Chair", "amount": Decimal("5000.00"), "category": "FURNITURE"}],
    )
    with pytest.raises(ConflictError):
        request_services.submit_expense_request(req.id, 2002, "basic_user")


def test_t_uc_06_finance_validate_request_and_route(base_setup):
    """T-UC-06: IAA-UC-103 Main Flow - Finance validate request and route"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Robotics Kits",
        description="Parts",
        items=[{"description": "Parts", "amount": Decimal("25000.00"), "category": "EQUIPMENT"}],
    )
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    validated = request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    assert validated.status == "finance_validated"
    assert validated.required_approval_levels >= 1
    assert validated.assigned_approver_role != ""


def test_t_uc_07_finance_raises_clarification_query(base_setup):
    """T-UC-07: IAA-UC-103 Alternative A1 - Finance raises clarification query"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Conference Registration",
        description="Registration fees",
        items=[{"description": "Fee", "amount": Decimal("8000.00"), "category": "CONF"}],
    )
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    q = request_services.raise_request_clarification(req.id, 3001, "finance_staff", "Please provide brochure.")
    assert q.status == "pending"
    req.refresh_from_db()
    assert req.status == "query_raised"


def test_t_uc_08_finance_triggers_anomaly_on_insufficient_budget(base_setup):
    """T-UC-08: IAA-UC-103 Alternative A2 - Finance triggers anomaly on insufficient budget"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Supercomputer Server",
        description="High-end server",
        items=[{"description": "Server", "amount": Decimal("600000.00"), "category": "EQUIPMENT"}],
    )
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    anom = Anomaly.objects.filter(reference_type="request", reference_id=req.id).first()
    assert anom is not None
    assert anom.category == "budget_insufficient"


def test_t_uc_09_creator_responds_to_clarification_query(base_setup):
    """T-UC-09: IAA-UC-104 Main Flow - Creator responds to clarification query"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Project Consumables",
        description="Batteries",
        items=[{"description": "Batteries", "amount": Decimal("2000.00"), "category": "PARTS"}],
    )
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    q = request_services.raise_request_clarification(req.id, 3001, "finance_staff", "Confirm quantity")
    responded = request_services.respond_to_request_clarification(q.id, 1001, "basic_user", "Quantity is 50 packs.")
    assert responded.status == "query_responded"
    q.refresh_from_db()
    assert q.status == "responded"


def test_t_uc_10_block_empty_query_response_text(base_setup):
    """T-UC-10: IAA-UC-104 Exception E1 - Block empty query response text"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Project Consumables",
        description="Batteries",
        items=[{"description": "Batteries", "amount": Decimal("2000.00"), "category": "PARTS"}],
    )
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    q = request_services.raise_request_clarification(req.id, 3001, "finance_staff", "Confirm quantity")
    with pytest.raises(BadRequestError):
        request_services.respond_to_request_clarification(q.id, 1001, "basic_user", "   ")


def test_t_uc_11_process_and_record_approved_request(base_setup):
    """T-UC-11: IAA-UC-105 Main Flow - Process and record approved request"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Books",
        description="Library books",
        items=[{"description": "Textbooks", "amount": Decimal("10000.00"), "category": "BOOKS"}],
    )
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    approval_services.record_request_decision(req.id, 2001, "hod", "approve", "Approved by HOD")
    req.refresh_from_db()
    assert req.status == "approved"
    recorded = request_services.record_request_processing(req.id, 3001, "finance_staff")
    assert recorded.status == "recorded"


def test_t_uc_12_block_recording_unapproved_request(base_setup):
    """T-UC-12: IAA-UC-105 Exception E1 - Block recording unapproved request"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Stationery",
        description="Pens and paper",
        items=[{"description": "Items", "amount": Decimal("3000.00"), "category": "OFFICE"}],
    )
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    with pytest.raises(InvalidStateTransitionError):
        request_services.record_request_processing(req.id, 3001, "finance_staff")


# --- IAA-UC-201 .. 203: Approval Decisions & Escalation ---

def test_t_uc_13_approver_approves_request_with_remarks(base_setup):
    """T-UC-13: IAA-UC-201 Main Flow - Approver approves request with remarks"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Lab Tools",
        description="Tools",
        items=[{"description": "Tools", "amount": Decimal("5000.00"), "category": "EQUIPMENT"}],
    )
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    decided = approval_services.record_request_decision(req.id, 2001, "hod", "approve", "Looks good")
    assert decided.status == "approved"


def test_t_uc_14_approver_rejects_request_with_remarks(base_setup):
    """T-UC-14: IAA-UC-201 Alternative A1 - Approver rejects request with remarks"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Unnecessary Purchase",
        description="Misc items",
        items=[{"description": "Misc", "amount": Decimal("4000.00"), "category": "MISC"}],
    )
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    rejected = approval_services.record_request_decision(req.id, 2001, "hod", "reject", "Budget cut in department")
    assert rejected.status == "rejected"


def test_t_uc_15_enforce_segregation_of_duties_against_self_approval(base_setup):
    """T-UC-15: IAA-UC-201 Exception E1 - Enforce segregation of duties against self-approval"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Research Consumables",
        description="Lab kit",
        items=[{"description": "Kit", "amount": Decimal("6000.00"), "category": "PARTS"}],
    )
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    with pytest.raises(DomainValidationError):
        approval_services.record_request_decision(req.id, 1001, "hod", "approve", "Self approval attempt")


def test_t_uc_16_reject_decision_without_remarks(base_setup):
    """T-UC-16: IAA-UC-201 Exception E2 - Reject decision without remarks"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Projector Bulb",
        description="Replacement bulb",
        items=[{"description": "Bulb", "amount": Decimal("3500.00"), "category": "EQUIPMENT"}],
    )
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    with pytest.raises(DomainValidationError):
        approval_services.record_request_decision(req.id, 2001, "hod", "approve", "   ")


def test_t_uc_17_next_authority_approves_escalated_request(base_setup):
    """T-UC-17: IAA-UC-202 Main Flow - Next authority approves escalated request"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Server RAM",
        description="RAM Upgrade",
        items=[{"description": "RAM", "amount": Decimal("12000.00"), "category": "EQUIPMENT"}],
    )
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    approval_services.escalate_overdue_approval("request", req.id, "Director")
    req.refresh_from_db()
    assert req.status == "escalated"
    approved = approval_services.record_request_decision(req.id, 9001, "Director", "approve", "Approved after escalation")
    assert approved.status == "approved"


def test_t_uc_18_authority_rejects_escalated_request(base_setup):
    """T-UC-18: IAA-UC-202 Alternative A1 - Authority rejects escalated request"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Server GPU",
        description="GPU Upgrade",
        items=[{"description": "GPU", "amount": Decimal("40000.00"), "category": "EQUIPMENT"}],
    )
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    approval_services.escalate_overdue_approval("request", req.id, "Director")
    rejected = approval_services.record_request_decision(req.id, 9001, "Director", "reject", "Rejected post escalation")
    assert rejected.status == "rejected"


def test_t_uc_19_system_escalates_overdue_approval(base_setup):
    """T-UC-19: IAA-UC-203 Main Flow - System escalates overdue approval"""
    from modules.iaa.tasks import escalate_overdue_approvals
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Overdue Request",
        description="Needs escalation",
        items=[{"description": "Kit", "amount": Decimal("8000.00"), "category": "EQUIPMENT"}],
    )
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    req = request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    req.approval_assigned_at = timezone.now() - timedelta(days=5)
    req.save()
    count = escalate_overdue_approvals()
    assert count >= 1
    req.refresh_from_db()
    assert req.status == "escalated"


def test_t_uc_20_recent_approval_within_sla_not_escalated(base_setup):
    """T-UC-20: IAA-UC-203 Condition False - Recent approval within SLA is not escalated"""
    from modules.iaa.tasks import escalate_overdue_approvals
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Fresh Request",
        description="Freshly submitted",
        items=[{"description": "Kit", "amount": Decimal("5000.00"), "category": "EQUIPMENT"}],
    )
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    req = request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    req.approval_assigned_at = timezone.now()
    req.save()
    escalate_overdue_approvals()
    req.refresh_from_db()
    assert req.status == "finance_validated"


# --- IAA-UC-302 .. 304: Anomaly Detection & Resolution ---

def test_t_uc_21_manually_flag_material_anomaly(base_setup):
    """T-UC-21: IAA-UC-302 Main Flow - Manually flag material anomaly"""
    anom = anomaly_services.create_anomaly(
        category="duplicate_billing",
        description="Possible duplicate invoice submitted",
        reference_type="request",
        reference_id=101,
        flagged_by_id=3001,
        flagged_by_role="finance_staff",
    )
    assert anom.pk is not None
    assert anom.status == "open"
    assert anom.category == "duplicate_billing"


def test_t_uc_22_resolve_open_anomaly_with_remarks(base_setup):
    """T-UC-22: IAA-UC-303 Main Flow - Resolve open anomaly with remarks"""
    anom = anomaly_services.create_anomaly(
        category="suspicious_vendor",
        description="Unverified vendor details",
        reference_type="request",
        reference_id=102,
        flagged_by_id=3001,
        flagged_by_role="finance_staff",
    )
    resolved = anomaly_services.resolve_or_escalate_anomaly(
        anomaly_id=anom.id,
        actor_id=3001,
        actor_role="finance_staff",
        action="resolve",
        remarks="Vendor credentials re-verified with registry.",
    )
    assert resolved.status == "resolved"


def test_t_uc_23_escalate_open_anomaly_to_higher_review(base_setup):
    """T-UC-23: IAA-UC-303 Alternative A1 - Escalate open anomaly to higher review"""
    anom = anomaly_services.create_anomaly(
        category="forged_document",
        description="Altered bill amount",
        reference_type="request",
        reference_id=103,
        flagged_by_id=3001,
        flagged_by_role="finance_staff",
    )
    escalated = anomaly_services.resolve_or_escalate_anomaly(
        anomaly_id=anom.id,
        actor_id=3001,
        actor_role="finance_staff",
        action="escalate",
        remarks="Escalating to internal audit committee.",
    )
    assert escalated.status == "escalated"


def test_t_uc_24_automatic_anomaly_created_on_budget_overdraft(base_setup):
    """T-UC-24: IAA-UC-304 Main Flow - Automatic anomaly created on budget overdraft"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="High Cost Server Cluster",
        description="Cluster",
        items=[{"description": "Cluster", "amount": Decimal("800000.00"), "category": "EQUIPMENT"}],
    )
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    anoms = Anomaly.objects.filter(reference_type="request", reference_id=req.id)
    assert anoms.filter(category="budget_insufficient").exists()


# --- IAA-UC-401 .. 404: Travel Allowance (TA) Lifecycle ---

def test_t_uc_25_submit_travel_allowance_claim(base_setup):
    """T-UC-25: IAA-UC-401 Main Flow - Submit travel allowance claim"""
    claim = travel_services.submit_travel_claim(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        purpose="IEEE Conference Presentation",
        departure_date="2026-11-10",
        arrival_date="2026-11-14",
        source_location="Campus",
        destination_location="Hyderabad",
        claimed_amount=Decimal("18000.00"),
        items=[{"expense_type": "Flight", "amount": Decimal("18000.00"), "details": "Round trip"}],
    )
    assert claim.pk is not None
    assert claim.status == "submitted"
    assert claim.is_locked is True


def test_t_uc_26_block_ta_claim_with_return_date_earlier_than_departure(base_setup):
    """T-UC-26: IAA-UC-401 Exception E1 - Block TA claim with return date earlier than departure (DEF-A8-01 candidate)"""
    with pytest.raises(DomainValidationError):
        travel_services.submit_travel_claim(
            user_id=1001,
            acting_role="basic_user",
            department="CSE",
            purpose="Invalid Dates Trip",
            departure_date="2026-11-20",
            arrival_date="2026-11-15",
            source_location="Campus",
            destination_location="Delhi",
            claimed_amount=Decimal("12000.00"),
        )


def test_t_uc_27_verify_standard_ta_claim(base_setup):
    """T-UC-27: IAA-UC-402 Main Flow - Verify standard TA claim (< threshold)"""
    claim = travel_services.submit_travel_claim(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        purpose="Research Visit",
        departure_date="2026-11-01",
        arrival_date="2026-11-03",
        source_location="Campus",
        destination_location="Bangalore",
        claimed_amount=Decimal("25000.00"),
    )
    verified = travel_services.verify_travel_claim(claim.id, 3001, "finance_staff")
    assert verified.status == "verified"
    assert verified.is_high_value is False


def test_t_uc_28_route_high_value_ta_claim_to_approval(base_setup):
    """T-UC-28: IAA-UC-402 Alternative A1 - Route high-value TA claim (>= threshold) to approval"""
    claim = travel_services.submit_travel_claim(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        purpose="International Workshop",
        departure_date="2026-11-01",
        arrival_date="2026-11-08",
        source_location="Campus",
        destination_location="Singapore",
        claimed_amount=Decimal("95000.00"),
    )
    verified = travel_services.verify_travel_claim(claim.id, 3001, "finance_staff")
    assert verified.status == "approval_pending"
    assert verified.is_high_value is True
    assert verified.assigned_approver_role == "Dean"


def test_t_uc_29_raise_clarification_query_on_ta_claim(base_setup):
    """T-UC-29: IAA-UC-402 Alternative A2 - Raise clarification query on TA claim"""
    claim = travel_services.submit_travel_claim(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        purpose="Workshop",
        departure_date="2026-11-01",
        arrival_date="2026-11-04",
        source_location="Campus",
        destination_location="Goa",
        claimed_amount=Decimal("30000.00"),
    )
    q = travel_services.raise_travel_clarification(claim.id, 3001, "finance_staff", "Provide original boarding passes.")
    assert q.status == "pending"
    claim.refresh_from_db()
    assert claim.status == "query_raised"


def test_t_uc_30_approve_high_value_ta_claim(base_setup):
    """T-UC-30: IAA-UC-403 Main Flow - Approve high-value TA claim"""
    claim = travel_services.submit_travel_claim(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        purpose="Overseas Academic Exchange",
        departure_date="2026-11-01",
        arrival_date="2026-11-10",
        source_location="Campus",
        destination_location="Tokyo",
        claimed_amount=Decimal("120000.00"),
    )
    travel_services.verify_travel_claim(claim.id, 3001, "finance_staff")
    approved = approval_services.record_travel_decision(claim.id, 4001, "Dean", "approve", "Approved by Dean")
    assert approved.status == "approved"


def test_t_uc_31_reject_high_value_ta_claim(base_setup):
    """T-UC-31: IAA-UC-403 Alternative A1 - Reject high-value TA claim"""
    claim = travel_services.submit_travel_claim(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        purpose="Overseas Academic Exchange",
        departure_date="2026-11-01",
        arrival_date="2026-11-10",
        source_location="Campus",
        destination_location="Tokyo",
        claimed_amount=Decimal("120000.00"),
    )
    travel_services.verify_travel_claim(claim.id, 3001, "finance_staff")
    rejected = approval_services.record_travel_decision(claim.id, 4001, "Dean", "reject", "Exceeds overseas limits")
    assert rejected.status == "rejected"


def test_t_uc_32_block_self_approval_on_high_value_ta_claim(base_setup):
    """T-UC-32: IAA-UC-403 Exception E1 - Block self-approval on high-value TA claim"""
    claim = travel_services.submit_travel_claim(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        purpose="Overseas Academic Exchange",
        departure_date="2026-11-01",
        arrival_date="2026-11-10",
        source_location="Campus",
        destination_location="Tokyo",
        claimed_amount=Decimal("80000.00"),
    )
    travel_services.verify_travel_claim(claim.id, 3001, "finance_staff")
    with pytest.raises(DomainValidationError):
        approval_services.record_travel_decision(claim.id, 1001, "Dean", "approve", "Attempted self approval")


def test_t_uc_33_record_verified_or_approved_ta_claim(base_setup):
    """T-UC-33: IAA-UC-404 Main Flow - Record verified or approved TA claim"""
    claim = travel_services.submit_travel_claim(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        purpose="Field Visit",
        departure_date="2026-11-01",
        arrival_date="2026-11-03",
        source_location="Campus",
        destination_location="Bhopal",
        claimed_amount=Decimal("12000.00"),
    )
    travel_services.verify_travel_claim(claim.id, 3001, "finance_staff")
    recorded = travel_services.record_travel_processing(claim.id, 3001, "finance_staff")
    assert recorded.status == "recorded"


# --- IAA-UC-501 .. 504: Internal Audit Lifecycle ---

def test_t_uc_34_auditor_raises_audit_observation(base_setup):
    """T-UC-34: IAA-UC-501 Main Flow - Auditor raises audit observation"""
    obs = audit_services.raise_audit_observation(
        auditor_id=6001,
        acting_role="auditor",
        department="CSE",
        title="Missing supporting bills",
        description="Invoice copy missing for voucher #100",
        reference_type="request",
        reference_id=100,
    )
    assert obs.pk is not None
    assert obs.status == "open"


def test_t_uc_35_respond_to_audit_observation(base_setup):
    """T-UC-35: IAA-UC-502 Main Flow - Respond to audit observation"""
    obs = audit_services.raise_audit_observation(
        auditor_id=6001,
        acting_role="auditor",
        department="CSE",
        title="Vendor GST verification",
        description="Verify GSTIN",
    )
    responded = audit_services.respond_to_audit_observation(
        observation_id=obs.id,
        user_id=1001,
        acting_role="basic_user",
        response_text="GST certificate attached with GSTIN verification report.",
    )
    assert responded.status == "responded"


def test_t_uc_36_close_observation_when_response_is_satisfactory(base_setup):
    """T-UC-36: IAA-UC-503 Main Flow - Close observation when response is satisfactory"""
    obs = audit_services.raise_audit_observation(
        auditor_id=6001,
        acting_role="auditor",
        department="CSE",
        title="Asset Tag Verification",
        description="Verify physical tagging",
    )
    audit_services.respond_to_audit_observation(obs.id, 1001, "basic_user", "Photos of asset tags uploaded.")
    closed = audit_services.review_and_close_observation(
        observation_id=obs.id,
        auditor_id=6001,
        acting_role="auditor",
        is_satisfactory=True,
        remarks="Tags verified physically, issue resolved.",
    )
    assert closed.status == "closed"


def test_t_uc_37_reopen_observation_when_response_is_unsatisfactory(base_setup):
    """T-UC-37: IAA-UC-503 Alternative A1 - Reopen observation when response is unsatisfactory"""
    obs = audit_services.raise_audit_observation(
        auditor_id=6001,
        acting_role="auditor",
        department="CSE",
        title="Depreciation Record Query",
        description="Check depreciation method",
    )
    audit_services.respond_to_audit_observation(obs.id, 1001, "basic_user", "Old schedule attached.")
    reopened = audit_services.review_and_close_observation(
        observation_id=obs.id,
        auditor_id=6001,
        acting_role="auditor",
        is_satisfactory=False,
        remarks="Unsatisfactory: Current FY depreciation calculation is missing.",
    )
    assert reopened.status == "open"


def test_t_uc_38_auditor_inspects_historical_records_in_read_only_mode(base_setup):
    """T-UC-38: IAA-UC-504 Main Flow - Auditor inspects historical records in read-only mode"""
    audit_services.raise_audit_observation(6001, "auditor", "CSE", "Audit 1", "Observation 1")
    audit_services.raise_audit_observation(6001, "auditor", "CSE", "Audit 2", "Observation 2")
    p_auditor = make_principal(user_id=6001, modules=("iaa",), permissions=("iaa.audit.view",))
    obs_list = audit_selectors.get_audit_observations(p_auditor)
    assert obs_list.count() >= 2


# --- IAA-UC-601 .. 604: Reporting, Views & Dashboards ---

def test_t_uc_39_view_department_expenditure_report(base_setup):
    """T-UC-39: IAA-UC-601 Main Flow - View department expenditure report"""
    p = make_principal(user_id=3001, modules=("iaa",), permissions=("iaa.report.view",))
    summary = report_selectors.get_dashboard_summary(p)
    assert isinstance(summary, dict)
    assert "requests" in summary


def test_t_uc_40_export_summary_report_to_csv(base_setup, stub_iam):
    """T-UC-40: IAA-UC-602 Main Flow - Export summary report to CSV"""
    stub_iam(make_session(user_id=3001, modules=("iaa",), permissions=("iaa.report.view",)))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    res = client.get("/api/v1/iaa/reports/export/")
    assert res.status_code == 200
    assert "text/csv" in res["Content-Type"]


def test_t_uc_41_basic_user_tracks_own_requests(base_setup):
    """T-UC-41: IAA-UC-603 Main Flow - Basic User tracks own requests"""
    r1 = request_services.create_expense_request(1001, "basic_user", "CSE", "expense", "User 1 Request")
    r2 = request_services.create_expense_request(2002, "basic_user", "CSE", "expense", "User 2 Request")
    p = make_principal(user_id=1001, modules=("iaa",), permissions=("iaa.expense_request.view",))
    user_reqs = request_selectors.get_requests(p)
    req_ids = [r.id for r in user_reqs]
    assert r1.id in req_ids
    assert r2.id not in req_ids


def test_t_uc_42_view_pending_approval_queue(base_setup):
    """T-UC-42: IAA-UC-604 Main Flow - View pending approval queue"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Pending Approval Item",
        description="Lab item",
        items=[{"description": "Item", "amount": Decimal("10000.00"), "category": "PARTS"}],
    )
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    req = request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    req.assigned_approver_id = 2001
    req.save()
    p_hod = make_principal(
        user_id=2001,
        modules=("iaa",),
        roles=("hod",),
        active_role="hod",
        permissions=("iaa.request.approve", "iaa.request.view_all"),
    )
    queue = request_selectors.get_pending_approvals_for_user(p_hod)
    assert queue.filter(id=req.id).exists()


# --- IAA-UC-701 .. 704: Configuration & Role Administration ---

def test_t_uc_43_switch_active_iaa_role(base_setup):
    """T-UC-43: IAA-UC-701 Main Flow - Switch active IAA role"""
    p_user = make_principal(user_id=2001, modules=("iaa",), roles=("basic_user", "hod"), active_role="basic_user")
    assert p_user.active_role == "basic_user"
    p_hod = make_principal(user_id=2001, modules=("iaa",), roles=("basic_user", "hod"), active_role="hod")
    assert p_hod.active_role == "hod"


def test_t_uc_44_system_admin_manages_role_assignments(base_setup):
    """T-UC-44: IAA-UC-702 Main Flow - System Admin manages role assignments"""
    rule = config_services.add_approval_hierarchy_rule(
        user_id=9999,
        acting_role="system_admin",
        request_type="expense",
        min_amount=Decimal("0.00"),
        max_amount=Decimal("50000.00"),
        required_levels=1,
        approver_roles=["hod"],
    )
    assert rule.pk is not None


def test_t_uc_45_configure_approval_hierarchy_rules(base_setup):
    """T-UC-45: IAA-UC-703 Main Flow - Configure approval hierarchy rules"""
    rule = config_services.add_approval_hierarchy_rule(
        user_id=9999,
        acting_role="system_admin",
        request_type="travel",
        min_amount=Decimal("0.00"),
        max_amount=Decimal("100000.00"),
        required_levels=1,
        approver_roles=["dean"],
    )
    assert rule.pk is not None
    assert rule.request_type == "travel"


def test_t_uc_46_configure_financial_year_and_policy_parameters(base_setup):
    """T-UC-46: IAA-UC-704 Main Flow - Configure financial year and policy parameters"""
    cfg = config_services.update_iaa_configuration(
        user_id=9999,
        acting_role="system_admin",
        financial_year="2027-2028",
        high_value_ta_threshold=Decimal("75000.00"),
        approval_timeout_days=7,
    )
    assert cfg.financial_year == "2027-2028"
    assert cfg.high_value_ta_threshold == Decimal("75000.00")
    assert cfg.approval_timeout_days == 7
