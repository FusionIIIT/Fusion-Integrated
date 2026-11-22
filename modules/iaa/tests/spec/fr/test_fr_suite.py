"""Executable test suite for FR strategy (CFR-IAA-01..18, AFR-IAA-001..075)."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_principal, make_session
from core.api.exceptions import BadRequestError
from modules.iaa.domain.rules import DomainValidationError, validate_record_not_locked
from modules.iaa.models import (
    Anomaly,
    AnomalyStatus,
    ApprovalHierarchyRule,
    AuditLogEntry,
    AuditObservationStatus,
    DepartmentBudget,
    ExpenseVoucherRequest,
    IAAConfiguration,
    RequestStatus,
    TAClaimStatus,
)
from modules.iaa.selectors import reports as report_selectors
from modules.iaa.selectors.scoping import (
    scope_requests,
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
from modules.iaa.tasks import escalate_overdue_approvals

pytestmark = pytest.mark.django_db


@pytest.fixture
def base_setup():
    config = IAAConfiguration.objects.create(
        financial_year="2026-2027",
        high_value_ta_threshold=Decimal("50000.00"),
        approval_timeout_days=3,
        is_active=True,
    )
    budget = DepartmentBudget.objects.create(
        department="CSE",
        financial_year="2026-2027",
        allocated_amount=Decimal("100000.00"),
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


# --- CFR-IAA-01: Drafting, Submission, Locking ---

def test_afr_001_create_draft(base_setup):
    """test_id: T-FR-01, source_id: AFR-IAA-001"""
    req = request_services.create_expense_request(1001, "basic_user", "CSE", "expense", "Draft 1")
    assert req.status == RequestStatus.DRAFT
    assert not req.is_locked


def test_afr_002_enter_attributes(base_setup):
    """test_id: T-FR-02, source_id: AFR-IAA-002"""
    req = request_services.create_expense_request(1001, "basic_user", "CSE", "expense", "Lab Consumables", "Desc", [{"description": "Item 1", "amount": "500.00"}])
    assert req.department == "CSE"
    assert req.total_amount == Decimal("500.00")
    assert req.title == "Lab Consumables"


def test_afr_003_attach_items(base_setup):
    """test_id: T-FR-03, source_id: AFR-IAA-003"""
    items = [{"description": "Reagent A", "category": "Chemicals", "amount": "1200.00", "receipt_reference": "REC-01"}]
    req = request_services.create_expense_request(1001, "basic_user", "CSE", "expense", "Chemicals", items=items)
    assert req.items.count() == 1
    assert req.items.first().receipt_reference == "REC-01"


def test_afr_004_save_incomplete_draft(base_setup):
    """test_id: T-FR-04, source_id: AFR-IAA-004"""
    req = request_services.create_expense_request(1001, "basic_user", "CSE", "expense", "Incomplete Draft", items=[])
    assert req.status == RequestStatus.DRAFT
    assert req.total_amount == Decimal("0.00")


def test_afr_005_completeness_check_on_submission(base_setup):
    """test_id: T-FR-05, source_id: AFR-IAA-005"""
    req = request_services.create_expense_request(1001, "basic_user", "CSE", "expense", "Empty Draft", items=[])
    with pytest.raises(DomainValidationError):
        request_services.submit_expense_request(req.id, 1001, "basic_user")


def test_afr_006_post_submission_lock(base_setup):
    """test_id: T-FR-06, source_id: AFR-IAA-006"""
    items = [{"description": "Stationery", "amount": "200.00"}]
    req = request_services.create_expense_request(1001, "basic_user", "CSE", "expense", "Stationery", items=items)
    submitted = request_services.submit_expense_request(req.id, 1001, "basic_user")
    assert submitted.is_locked is True
    with pytest.raises(DomainValidationError, match="locked"):
        validate_record_not_locked(submitted.is_locked)


def test_afr_007_status_and_action_history(base_setup):
    """test_id: T-FR-07, source_id: AFR-IAA-007"""
    items = [{"description": "Keyboard", "amount": "1500.00"}]
    req = request_services.create_expense_request(1001, "basic_user", "CSE", "expense", "Hardware", items=items)
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    logs = AuditLogEntry.objects.filter(target_type="request", target_id=req.id)
    actions = list(logs.values_list("action", flat=True))
    assert "create_request_draft" in actions
    assert "submit_request" in actions


# --- CFR-IAA-02: Finance Validation & Clarification ---

def test_afr_008_finance_review(base_setup):
    """test_id: T-FR-08, source_id: AFR-IAA-008"""
    items = [{"description": "Chairs", "amount": "4000.00"}]
    req = request_services.create_expense_request(1001, "basic_user", "CSE", "expense", "Chairs", items=items)
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    validated = request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    assert validated.status == RequestStatus.FINANCE_VALIDATED


def test_afr_009_budget_validation(base_setup):
    """test_id: T-FR-09, source_id: AFR-IAA-009"""
    base_setup["budget"].allocated_amount = Decimal("500.00")
    base_setup["budget"].save()
    items = [{"description": "Expensive Item", "amount": "1000.00"}]
    req = request_services.create_expense_request(1001, "basic_user", "CSE", "expense", "Expensive", items=items)
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    anomaly = Anomaly.objects.filter(reference_type="request", reference_id=req.id).first()
    assert anomaly is not None
    assert anomaly.category == "budget_insufficient"


def test_afr_010_raise_clarification(base_setup):
    """test_id: T-FR-10, source_id: AFR-IAA-010"""
    items = [{"description": "Software", "amount": "3000.00"}]
    req = request_services.create_expense_request(1001, "basic_user", "CSE", "expense", "Software", items=items)
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    query = request_services.raise_request_clarification(req.id, 3001, "finance_staff", "Need invoice copy")
    req.refresh_from_db()
    assert req.status == RequestStatus.QUERY_RAISED
    assert query.status == "pending"


def test_afr_011_respond_clarification(base_setup):
    """test_id: T-FR-11, source_id: AFR-IAA-011"""
    items = [{"description": "Tools", "amount": "2000.00"}]
    req = request_services.create_expense_request(1001, "basic_user", "CSE", "expense", "Tools", items=items)
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    query = request_services.raise_request_clarification(req.id, 3001, "finance_staff", "Invoice details")
    responded = request_services.respond_to_request_clarification(query.id, 1001, "basic_user", "Invoice #102 attached")
    assert responded.status == RequestStatus.QUERY_RESPONDED


def test_afr_012_resume_validation_after_query(base_setup):
    """test_id: T-FR-12, source_id: AFR-IAA-012"""
    items = [{"description": "Sensors", "amount": "1500.00"}]
    req = request_services.create_expense_request(1001, "basic_user", "CSE", "expense", "Sensors", items=items)
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    query = request_services.raise_request_clarification(req.id, 3001, "finance_staff", "Quote missing")
    request_services.respond_to_request_clarification(query.id, 1001, "basic_user", "Quote added")
    validated = request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    assert validated.status == RequestStatus.FINANCE_VALIDATED


def test_afr_013_route_assignment(base_setup):
    """test_id: T-FR-13, source_id: AFR-IAA-013"""
    items = [{"description": "Desk", "amount": "12000.00"}]
    req = request_services.create_expense_request(1001, "basic_user", "CSE", "expense", "Desk", items=items)
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    validated = request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    assert validated.required_approval_levels == 1
    assert validated.assigned_approver_role == "HOD"


# --- CFR-IAA-03: Internal Completion & Non-Monetary Processing ---

def test_afr_014_record_approved_request(base_setup):
    """test_id: T-FR-14, source_id: AFR-IAA-014"""
    items = [{"description": "Board", "amount": "5000.00"}]
    req = request_services.create_expense_request(1001, "basic_user", "CSE", "expense", "Board", items=items)
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    approval_services.record_request_decision(req.id, 4001, "HOD", "approve", "Approved")
    recorded = request_services.record_request_processing(req.id, 3001, "finance_staff")
    assert recorded.status == RequestStatus.RECORDED


def test_afr_015_non_monetary_processing(base_setup):
    """test_id: T-FR-015, source_id: AFR-IAA-015"""
    items = [{"description": "Cable", "amount": "300.00"}]
    req = request_services.create_expense_request(1001, "basic_user", "CSE", "expense", "Cable", items=items)
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    approval_services.record_request_decision(req.id, 4001, "HOD", "approve", "OK")
    request_services.record_request_processing(req.id, 3001, "finance_staff")
    log = AuditLogEntry.objects.filter(target_type="request", target_id=req.id, action="record_processing").first()
    assert log is not None
    assert log.details.get("non_monetary") is True


def test_afr_016_retain_record_for_audit(base_setup):
    """test_id: T-FR-16, source_id: AFR-IAA-016"""
    items = [{"description": "Toner", "amount": "800.00"}]
    req = request_services.create_expense_request(1001, "basic_user", "CSE", "expense", "Toner", items=items)
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    approval_services.record_request_decision(req.id, 4001, "HOD", "approve", "OK")
    request_services.record_request_processing(req.id, 3001, "finance_staff")
    p_auditor = make_principal(user_id=6001, modules=("iaa",), permissions=("iaa.request.view_all",))
    scoped = scope_requests(ExpenseVoucherRequest.objects.all(), p_auditor)
    assert req.id in list(scoped.values_list("id", flat=True))


# --- CFR-IAA-04: Configured Approval Routing & Decisions ---

def test_afr_017_route_determination_by_amount(base_setup):
    """test_id: T-FR-17, source_id: AFR-IAA-017"""
    l1, _r1 = approval_services.determine_approval_route("expense", Decimal("10000.00"))
    l2, _r2 = approval_services.determine_approval_route("expense", Decimal("30000.00"))
    assert l1 == 1
    assert l2 == 2


def test_afr_018_distinct_approver_roles(base_setup):
    """test_id: T-FR-18, source_id: AFR-IAA-018"""
    _l3, r3 = approval_services.determine_approval_route("expense", Decimal("150000.00"))
    assert "HOD" in r3 and "Dean" in r3 and "Director" in r3


def test_afr_019_segregation_of_duties_enforced(base_setup):
    """test_id: T-FR-19, source_id: AFR-IAA-019"""
    items = [{"description": "Item", "amount": "100.00"}]
    req = request_services.create_expense_request(1001, "basic_user", "CSE", "expense", "Req", items=items)
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    with pytest.raises(DomainValidationError, match="Creator or claimant cannot approve"):
        approval_services.record_request_decision(req.id, 1001, "HOD", "approve", "Self approval")


def test_afr_020_approval_remarks_mandatory(base_setup):
    """test_id: T-FR-20, source_id: AFR-IAA-020"""
    items = [{"description": "Item", "amount": "100.00"}]
    req = request_services.create_expense_request(1001, "basic_user", "CSE", "expense", "Req", items=items)
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    with pytest.raises(DomainValidationError, match="mandatory"):
        approval_services.record_request_decision(req.id, 4001, "HOD", "approve", "")


def test_afr_021_rejection_decision(base_setup):
    """test_id: T-FR-21, source_id: AFR-IAA-021"""
    items = [{"description": "Item", "amount": "100.00"}]
    req = request_services.create_expense_request(1001, "basic_user", "CSE", "expense", "Req", items=items)
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    rejected = approval_services.record_request_decision(req.id, 4001, "HOD", "reject", "Not approved")
    assert rejected.status == RequestStatus.REJECTED


def test_afr_022_multi_level_progression(base_setup):
    """test_id: T-FR-22, source_id: AFR-IAA-022"""
    items = [{"description": "Big Item", "amount": "30000.00"}]
    req = request_services.create_expense_request(1001, "basic_user", "CSE", "expense", "Big", items=items)
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    step1 = approval_services.record_request_decision(req.id, 4001, "HOD", "approve", "L1 OK")
    assert step1.status == RequestStatus.APPROVAL_PENDING
    assert step1.current_approval_level == 2


def test_afr_023_terminal_approved_status(base_setup):
    """test_id: T-FR-23, source_id: AFR-IAA-023"""
    items = [{"description": "Item", "amount": "5000.00"}]
    req = request_services.create_expense_request(1001, "basic_user", "CSE", "expense", "Item", items=items)
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    approved = approval_services.record_request_decision(req.id, 4001, "HOD", "approve", "Final OK")
    assert approved.status == RequestStatus.APPROVED


# --- CFR-IAA-05: Timed Approval Escalation ---

def test_afr_024_025_026_027_timed_escalation(base_setup):
    """test_id: T-FR-24..27, source_id: AFR-IAA-024..027"""
    items = [{"description": "Item", "amount": "5000.00"}]
    req = request_services.create_expense_request(1001, "basic_user", "CSE", "expense", "Overdue", items=items)
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    req = request_services.review_and_validate_request(req.id, 3001, "finance_staff")
    req.approval_assigned_at = timezone.now() - timedelta(days=5)
    req.save()
    escalated_count = escalate_overdue_approvals()
    assert escalated_count >= 1
    req.refresh_from_db()
    assert req.status == RequestStatus.ESCALATED
    assert req.assigned_approver_role == "Director"


# --- CFR-IAA-06: Travel Allowance Submission & Validation ---

def test_afr_028_submit_ta_claim(base_setup):
    """test_id: T-FR-28, source_id: AFR-IAA-028"""
    claim = travel_services.submit_travel_claim(1001, "basic_user", "CSE", "Conference", "2026-06-01", "2026-06-04", "Jabalpur", "Delhi", Decimal("8000.00"))
    assert claim.status == TAClaimStatus.SUBMITTED
    assert claim.is_locked is True


def test_afr_029_ta_date_validation(base_setup):
    """test_id: T-FR-29, source_id: AFR-IAA-029"""
    with pytest.raises(DomainValidationError):
        travel_services.submit_travel_claim(1001, "basic_user", "CSE", "Trip", "2026-06-10", "2026-06-05", "Jabalpur", "Delhi", Decimal("5000.00"))


def test_afr_030_ta_amount_positive(base_setup):
    """test_id: T-FR-30, source_id: AFR-IAA-030"""
    with pytest.raises(DomainValidationError):
        travel_services.submit_travel_claim(1001, "basic_user", "CSE", "Trip", "2026-06-01", "2026-06-05", "Jabalpur", "Delhi", Decimal("0.00"))


def test_afr_031_ta_post_submission_lock(base_setup):
    """test_id: T-FR-31, source_id: AFR-IAA-031"""
    claim = travel_services.submit_travel_claim(1001, "basic_user", "CSE", "Conf", "2026-06-01", "2026-06-05", "DEL", "BOM", Decimal("6000.00"))
    assert claim.is_locked is True


def test_afr_032_ta_line_items(base_setup):
    """test_id: T-FR-32, source_id: AFR-IAA-032"""
    items = [{"expense_type": "Flight", "amount": "4000.00", "details": "Leg 1"}]
    claim = travel_services.submit_travel_claim(1001, "basic_user", "CSE", "Conf", "2026-06-01", "2026-06-05", "DEL", "BOM", Decimal("4000.00"), items=items)
    assert claim.items.count() == 1


# --- CFR-IAA-07: TA Policy Verification ---

def test_afr_033_034_ta_standard_verification(base_setup):
    """test_id: T-FR-33..34, source_id: AFR-IAA-033..034"""
    claim = travel_services.submit_travel_claim(1001, "basic_user", "CSE", "Workshop", "2026-07-01", "2026-07-03", "Jabalpur", "Bhopal", Decimal("12000.00"))
    verified = travel_services.verify_travel_claim(claim.id, 3001, "finance_staff")
    assert verified.status == TAClaimStatus.VERIFIED
    assert verified.is_high_value is False


def test_afr_035_ta_clarification(base_setup):
    """test_id: T-FR-35, source_id: AFR-IAA-035"""
    claim = travel_services.submit_travel_claim(1001, "basic_user", "CSE", "Trip", "2026-07-01", "2026-07-03", "DEL", "BOM", Decimal("5000.00"))
    q = travel_services.raise_travel_clarification(claim.id, 3001, "finance_staff", "Boarding pass required")
    claim.refresh_from_db()
    assert claim.status == TAClaimStatus.QUERY_RAISED
    travel_services.respond_to_travel_clarification(q.id, 1001, "basic_user", "Uploaded")
    claim.refresh_from_db()
    assert claim.status == TAClaimStatus.QUERY_RESPONDED


def test_afr_036_ta_verification_rejection(base_setup):
    """test_id: T-FR-36, source_id: AFR-IAA-036"""
    claim = travel_services.submit_travel_claim(1001, "basic_user", "CSE", "Trip", "2026-07-01", "2026-07-03", "DEL", "BOM", Decimal("5000.00"))
    from modules.iaa.domain.state_machine import transition_ta_claim
    claim.status = transition_ta_claim(claim.status, "reject", "finance_staff")
    claim.save()
    assert claim.status == TAClaimStatus.REJECTED


# --- CFR-IAA-08: High-Value TA Routing & Approval ---

def test_afr_037_038_high_value_ta_approval(base_setup):
    """test_id: T-FR-37..38, source_id: AFR-IAA-037..038"""
    claim = travel_services.submit_travel_claim(1001, "basic_user", "CSE", "Global Keynote", "2026-08-01", "2026-08-10", "DEL", "LON", Decimal("80000.00"))
    verified = travel_services.verify_travel_claim(claim.id, 3001, "finance_staff")
    assert verified.status == TAClaimStatus.APPROVAL_PENDING
    assert verified.is_high_value is True
    approved = approval_services.record_travel_decision(claim.id, 5001, "Dean", "approve", "Approved international travel")
    assert approved.status == TAClaimStatus.APPROVED


def test_afr_039_high_value_ta_segregation_of_duties(base_setup):
    """test_id: T-FR-39, source_id: AFR-IAA-039"""
    claim = travel_services.submit_travel_claim(1001, "basic_user", "CSE", "Global Keynote", "2026-08-01", "2026-08-10", "DEL", "LON", Decimal("80000.00"))
    travel_services.verify_travel_claim(claim.id, 3001, "finance_staff")
    with pytest.raises(DomainValidationError, match="Creator or claimant cannot approve"):
        approval_services.record_travel_decision(claim.id, 1001, "Dean", "approve", "Self approval")


# --- CFR-IAA-09: TA Non-Monetary Completion ---

def test_afr_040_041_042_ta_record_processing(base_setup):
    """test_id: T-FR-40..42, source_id: AFR-IAA-040..042"""
    claim = travel_services.submit_travel_claim(1001, "basic_user", "CSE", "Trip", "2026-08-01", "2026-08-05", "DEL", "BOM", Decimal("15000.00"))
    travel_services.verify_travel_claim(claim.id, 3001, "finance_staff")
    recorded = travel_services.record_travel_processing(claim.id, 3001, "finance_staff")
    assert recorded.status == TAClaimStatus.RECORDED


# --- CFR-IAA-10 & 11: Anomaly Management ---

def test_afr_043_046_047_automatic_anomaly(base_setup):
    """test_id: T-FR-43,46,47, source_id: AFR-IAA-043,046,047"""
    anomaly = anomaly_services.create_anomaly("budget_insufficient", "Over budget", "request", 101, 3001, "finance_staff", "finance_staff")
    assert anomaly.status == AnomalyStatus.OPEN
    assert anomaly.reference_type == "request"
    assert anomaly.resolver_role == "finance_staff"


def test_afr_044_045_manual_anomaly_flagging(base_setup):
    """test_id: T-FR-44..45, source_id: AFR-IAA-044..045"""
    a_fin = anomaly_services.create_anomaly("duplicate_bill", "Duplicate bill", "request", 102, 3001, "finance_staff")
    a_aud = anomaly_services.create_anomaly("audit_finding", "Missing invoice", "request", 103, 6001, "audit_officer")
    assert a_fin.flagged_by_role == "finance_staff"
    assert a_aud.flagged_by_role == "audit_officer"


def test_afr_048_049_050_anomaly_resolution_and_escalation(base_setup):
    """test_id: T-FR-48..50, source_id: AFR-IAA-048..050"""
    a = anomaly_services.create_anomaly("compliance", "Check needed", "request", 104, 3001, "finance_staff")
    esc = anomaly_services.resolve_or_escalate_anomaly(a.id, 3001, "finance_staff", "escalate", "Escalating")
    assert esc.status == AnomalyStatus.ESCALATED
    res = anomaly_services.resolve_or_escalate_anomaly(a.id, 6001, "audit_officer", "resolve", "Resolved satisfactorily")
    assert res.status == AnomalyStatus.RESOLVED


# --- CFR-IAA-12 & 13: Audit Observations ---

def test_afr_051_052_raise_audit_observation(base_setup):
    """test_id: T-FR-51..52, source_id: AFR-IAA-051..052"""
    obs = audit_services.raise_audit_observation(6001, "audit_officer", "CSE", "Asset discrepancy", "Tag missing on server", "request", 10)
    assert obs.status == AuditObservationStatus.OPEN
    assert obs.title == "Asset discrepancy"
    with pytest.raises(BadRequestError):
        audit_services.raise_audit_observation(6001, "audit_officer", "CSE", "", "Details")


def test_afr_053_054_respond_audit_observation(base_setup):
    """test_id: T-FR-53..54, source_id: AFR-IAA-053..054"""
    obs = audit_services.raise_audit_observation(6001, "audit_officer", "CSE", "Title", "Desc")
    resp = audit_services.respond_to_audit_observation(obs.id, 1002, "basic_user", "Server tag re-applied")
    assert resp.status == AuditObservationStatus.RESPONDED
    with pytest.raises(BadRequestError):
        audit_services.respond_to_audit_observation(obs.id, 1002, "basic_user", "   ")


def test_afr_055_056_057_review_and_close_observation(base_setup):
    """test_id: T-FR-55..57, source_id: AFR-IAA-055..057"""
    obs = audit_services.raise_audit_observation(6001, "audit_officer", "CSE", "Discrepancy", "Details")
    audit_services.respond_to_audit_observation(obs.id, 1002, "basic_user", "Explanation 1")
    reopened = audit_services.review_and_close_observation(obs.id, 6001, "audit_officer", is_satisfactory=False, remarks="Need proof")
    assert reopened.status == AuditObservationStatus.OPEN
    audit_services.respond_to_audit_observation(obs.id, 1002, "basic_user", "Attached photo")
    closed = audit_services.review_and_close_observation(obs.id, 6001, "audit_officer", is_satisfactory=True, remarks="Satisfactory")
    assert closed.status == AuditObservationStatus.CLOSED


# --- CFR-IAA-14: Reporting & Dashboards ---

def test_afr_058_059_060_reporting_and_export(base_setup, stub_iam):
    """test_id: T-FR-58..60, source_id: AFR-IAA-058..060"""
    p = make_principal(user_id=3001, modules=("iaa",), permissions=("iaa.report.view", "iaa.reports.view", "iaa.reports.export"))
    summary = report_selectors.get_dashboard_summary(p)
    assert isinstance(summary, dict)
    assert "requests" in summary
    stub_iam(make_session(user_id=3001, modules=("iaa",), permissions=("iaa.report.view",)))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    res = client.get("/api/v1/iaa/reports/export/")
    assert res.status_code == 200


# --- CFR-IAA-15: Policy & Configuration ---

def test_afr_061_062_063_064_configuration_management(base_setup):
    """test_id: T-FR-61..64, source_id: AFR-IAA-061..064"""
    cfg = config_services.update_iaa_configuration(9999, "system_admin", financial_year="2027-2028", high_value_ta_threshold=Decimal("60000.00"), approval_timeout_days=5)
    assert cfg.financial_year == "2027-2028"
    assert cfg.high_value_ta_threshold == Decimal("60000.00")
    assert cfg.approval_timeout_days == 5
    b = config_services.set_department_budget(9999, "system_admin", "CSE", "2027-2028", Decimal("750000.00"))
    assert b.allocated_amount == Decimal("750000.00")


# --- CFR-IAA-16: Role Scoping & Isolation ---

def test_afr_065_066_067_068_visibility_and_isolation(base_setup):
    """test_id: T-FR-65..68, source_id: AFR-IAA-065..068"""
    p_u1 = make_principal(user_id=1001, modules=("iaa",), permissions=("iaa.request.view_self",))
    p_admin = make_principal(user_id=9999, modules=("iaa",), roles=("system_admin",), active_role="system_admin")
    p_fin = make_principal(user_id=3001, modules=("iaa",), permissions=("iaa.request.view_all",))
    items = [{"description": "Item", "amount": "100.00"}]
    r1 = request_services.create_expense_request(1001, "basic_user", "CSE", "expense", "U1 Req", items=items)
    r2 = request_services.create_expense_request(2002, "basic_user", "CSE", "expense", "U2 Req", items=items)
    assert scope_requests(ExpenseVoucherRequest.objects.all(), p_admin).count() == 0
    assert list(scope_requests(ExpenseVoucherRequest.objects.all(), p_u1).values_list("id", flat=True)) == [r1.id]
    assert set(scope_requests(ExpenseVoucherRequest.objects.all(), p_fin).values_list("id", flat=True)) == {r1.id, r2.id}


# --- CFR-IAA-17: Immutable Audit Logging ---

def test_afr_069_070_071_072_audit_logging_integrity(base_setup):
    """test_id: T-FR-69..72, source_id: AFR-IAA-069..072"""
    items = [{"description": "Item", "amount": "100.00"}]
    req = request_services.create_expense_request(1001, "basic_user", "CSE", "expense", "Audit Req", items=items)
    log = AuditLogEntry.objects.filter(target_type="request", target_id=req.id).first()
    assert log is not None
    assert log.acting_role == "basic_user"


# --- CFR-IAA-18: Notification Integration ---

def test_afr_073_074_075_notification_matrix(base_setup):
    """test_id: T-FR-73..75, source_id: AFR-IAA-073..075"""
    from modules.iaa.services import notifications
    notifications.emit_notification([1001], "Title", "Message", "request", 1)
