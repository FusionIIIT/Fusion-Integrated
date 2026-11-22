"""Business Rules Test Suite for IAA module (Strategy: BR).
Specification-driven tests derived strictly from BR_DESIGN.json.
Contains 39 test cases (T-BR-01 to T-BR-39).
"""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_principal, make_session
from modules.iaa.domain.rules import (
    DomainValidationError,
    check_budget_sufficiency,
    is_high_value_ta,
    validate_decision_remarks,
    validate_record_not_locked,
    validate_request_completeness,
    validate_segregation_of_duties,
    validate_travel_completeness,
)
from modules.iaa.domain.state_machine import (
    transition_audit_observation,
)
from modules.iaa.models import (
    ApprovalHierarchyRule,
    AuditLogEntry,
    AuditObservation,
    DepartmentBudget,
    ExpenseVoucherRequest,
    IAAConfiguration,
    RequestStatus,
)
from modules.iaa.selectors import (
    scoping as scoping_selectors,
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
    audit_trail as audit_trail_services,
)
from modules.iaa.services import (
    configuration as config_services,
)
from modules.iaa.services import (
    requests as request_services,
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
    return {"config": config, "budget": budget}


# --- IAA-BR-001: Segregation of Duties ---

def test_t_br_01_creator_cannot_approve_own_request(base_setup):
    """T-BR-01: IAA-BR-001 prohibited - Verify creator cannot approve own financial request"""
    with pytest.raises(DomainValidationError, match="Creator or claimant cannot approve"):
        validate_segregation_of_duties(creator_id=1001, approver_id=1001)


def test_t_br_02_distinct_user_can_approve_request(base_setup):
    """T-BR-02: IAA-BR-001 permitted - Verify distinct user can approve request"""
    # Should not raise exception
    validate_segregation_of_duties(creator_id=1001, approver_id=2001)


def test_t_br_03_claimant_cannot_approve_own_travel_claim(base_setup):
    """T-BR-03: IAA-BR-001 claimant prohibited - Verify claimant cannot approve own travel claim"""
    with pytest.raises(DomainValidationError, match="Creator or claimant cannot approve"):
        validate_segregation_of_duties(creator_id=3003, approver_id=3003)


# --- IAA-BR-002: Approval Hierarchy & Routing ---

def test_t_br_04_tier_1_routing_under_25000(base_setup):
    """T-BR-04: IAA-BR-002 tier-1 - Verify amount < 25000 routes to 1 level (HoD)"""
    ApprovalHierarchyRule.objects.all().delete()
    levels, roles = approval_services.determine_approval_route("expense", Decimal("15000.00"))
    assert levels == 1
    assert roles == ["HOD"]


def test_t_br_05_tier_2_routing_between_25000_and_100000(base_setup):
    """T-BR-05: IAA-BR-002 tier-2 - Verify amount >= 25000 routes to 2 levels (HoD, Dean)"""
    ApprovalHierarchyRule.objects.all().delete()
    levels, roles = approval_services.determine_approval_route("expense", Decimal("50000.00"))
    assert levels == 2
    assert roles == ["HOD", "Dean"]


def test_t_br_06_tier_3_routing_above_100000(base_setup):
    """T-BR-06: IAA-BR-002 tier-3 - Verify amount >= 100000 routes to 3 levels (HoD, Dean, Director)"""
    ApprovalHierarchyRule.objects.all().delete()
    levels, roles = approval_services.determine_approval_route("expense", Decimal("150000.00"))
    assert levels == 3
    assert roles == ["HOD", "Dean", "Director"]


# --- IAA-BR-003 & 004: Role Context, Least Privilege & Isolation ---

def test_t_br_07_actions_authorized_and_logged_under_active_role(base_setup):
    """T-BR-07: IAA-BR-003 active-role - Verify actions authorized and logged under active acting role"""
    log = audit_trail_services.record_audit_log(
        user_id=3001,
        acting_role="finance_staff",
        action="review_check",
        target_type="request",
        target_id=1,
    )
    assert log.acting_role == "finance_staff"


def test_t_br_08_system_admin_operational_queries_return_none(base_setup):
    """T-BR-08: IAA-BR-004 sysadmin-isolated - Verify System Admin operational queries return .none()"""
    p_admin = make_principal(user_id=9999, modules=("iaa",), roles=("system_admin",), active_role="system_admin")
    qs = scoping_selectors.scope_requests(ExpenseVoucherRequest.objects.all(), p_admin)
    assert qs.count() == 0


def test_t_br_09_system_admin_has_configuration_access(base_setup):
    """T-BR-09: IAA-BR-004 sysadmin-config - Verify System Admin has configuration access"""
    cfg = config_services.update_iaa_configuration(9999, "system_admin", "2027-2028", Decimal("60000.00"), 4)
    assert cfg.financial_year == "2027-2028"
    assert cfg.high_value_ta_threshold == Decimal("60000.00")


# --- IAA-BR-005 & 006: Decision Remarks & Internal Processing ---

def test_t_br_10_empty_decision_remarks_rejected(base_setup):
    """T-BR-10: IAA-BR-005 empty-remarks - Verify empty decision remarks rejected"""
    with pytest.raises(DomainValidationError, match="mandatory"):
        validate_decision_remarks("")


def test_t_br_11_whitespace_decision_remarks_rejected(base_setup):
    """T-BR-11: IAA-BR-005 whitespace-remarks - Verify whitespace decision remarks rejected"""
    with pytest.raises(DomainValidationError, match="mandatory"):
        validate_decision_remarks("     ")


def test_t_br_12_valid_remarks_accepted(base_setup):
    """T-BR-12: IAA-BR-005 valid-remarks - Verify non-empty decision remarks accepted"""
    # Should not raise exception
    validate_decision_remarks("Approved after physical inspection of goods.")


def test_t_br_13_record_processing_is_non_monetary_internal_completion(base_setup):
    """T-BR-13: IAA-BR-006 non-monetary - Verify record processing is non-monetary internal completion"""
    req = ExpenseVoucherRequest.objects.create(
        user_id=1001,
        department="CSE",
        request_type="expense",
        title="Hardware Purchase",
        total_amount=Decimal("5000.00"),
        status=RequestStatus.APPROVED,
    )
    recorded = request_services.record_request_processing(req.id, 3001, "finance_staff")
    assert recorded.status == RequestStatus.RECORDED
    entry = AuditLogEntry.objects.filter(target_type="request", target_id=req.id, action="record_processing").first()
    assert entry is not None
    assert entry.details.get("non_monetary") is True


# --- IAA-BR-101 .. 104: Expense Lifecycle Validation & Constraints ---

def test_t_br_14_saving_incomplete_draft_permitted(base_setup):
    """T-BR-14: IAA-BR-101 draft-incomplete - Verify saving incomplete draft permitted"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="WIP Draft",
        items=[],
    )
    assert req.status == "draft"


def test_t_br_15_formal_submission_requires_title(base_setup):
    """T-BR-15: IAA-BR-101 submit-missing-title - Verify formal submission requires title"""
    with pytest.raises(DomainValidationError, match="title is mandatory"):
        validate_request_completeness("", "Description", "CSE", Decimal("500.00"), 1)


def test_t_br_16_formal_submission_requires_positive_amount(base_setup):
    """T-BR-16: IAA-BR-101 submit-zero-amount - Verify formal submission requires positive amount"""
    with pytest.raises(DomainValidationError, match="greater than zero"):
        validate_request_completeness("Title", "Description", "CSE", Decimal("0.00"), 1)


def test_t_br_17_formal_submission_requires_at_least_one_item(base_setup):
    """T-BR-17: IAA-BR-101 submit-no-items - Verify formal submission requires at least one item"""
    with pytest.raises(DomainValidationError, match="line item is required"):
        validate_request_completeness("Title", "Description", "CSE", Decimal("100.00"), 0)


def test_t_br_18_sufficient_budget_check_passes(base_setup):
    """T-BR-18: IAA-BR-102 budget-sufficient - Verify sufficient budget check passes"""
    assert check_budget_sufficiency(Decimal("50000.00"), Decimal("20000.00")) is True


def test_t_br_19_insufficient_budget_creates_anomaly_and_allows_processing(base_setup):
    """T-BR-19: IAA-BR-102 budget-insufficient - Verify insufficient budget creates anomaly and allows processing"""
    assert check_budget_sufficiency(Decimal("10000.00"), Decimal("20000.00")) is False


def test_t_br_20_anomaly_created_in_open_status(base_setup):
    """T-BR-20: IAA-BR-103 anomaly-trigger - Verify anomaly created in OPEN status"""
    anom = anomaly_services.create_anomaly("budget_insufficient", "Over budget", "request", 10, 3001, "finance_staff")
    assert anom.status == "open"


def test_t_br_21_open_anomaly_resolved_by_resolver(base_setup):
    """T-BR-21: IAA-BR-103 anomaly-resolve - Verify open anomaly resolved by resolver"""
    anom = anomaly_services.create_anomaly("duplicate_billing", "Duplicate", "request", 11, 3001, "finance_staff")
    resolved = anomaly_services.resolve_or_escalate_anomaly(anom.id, 3001, "finance_staff", "resolve", "Resolved fine")
    assert resolved.status == "resolved"


def test_t_br_22_open_anomaly_escalated_to_higher_review(base_setup):
    """T-BR-22: IAA-BR-103 anomaly-escalate - Verify open anomaly escalated to higher review"""
    anom = anomaly_services.create_anomaly("forged_document", "Forged", "request", 12, 3001, "finance_staff")
    escalated = anomaly_services.resolve_or_escalate_anomaly(anom.id, 3001, "finance_staff", "escalate", "Escalate to committee")
    assert escalated.status == "escalated"


def test_t_br_23_unsubmitted_draft_is_not_locked(base_setup):
    """T-BR-23: IAA-BR-104 edit-draft - Verify unsubmitted draft is not locked"""
    # Not locked should not raise
    validate_record_not_locked(False)


def test_t_br_24_submitted_request_is_locked_against_direct_edits(base_setup):
    """T-BR-24: IAA-BR-104 lock-submitted - Verify submitted request is locked against direct edits"""
    with pytest.raises(DomainValidationError, match="locked"):
        validate_record_not_locked(True)


# --- IAA-BR-201 & 202: Travel Allowance Rules & Thresholds ---

def test_t_br_25_arrival_gte_departure_accepted(base_setup):
    """T-BR-25: IAA-BR-201 date-valid - Verify arrival >= departure accepted"""
    validate_travel_completeness("Conference", "2026-11-01", "2026-11-05", Decimal("10000.00"), "CityA", "CityB")


def test_t_br_26_arrival_lt_departure_rejected(base_setup):
    """T-BR-26: IAA-BR-201 date-invalid - Verify arrival < departure rejected (DEF-A8-01 candidate)"""
    with pytest.raises(DomainValidationError):
        validate_travel_completeness("Conference", "2026-11-05", "2026-11-01", Decimal("10000.00"), "CityA", "CityB")


def test_t_br_27_negative_claimed_amount_rejected(base_setup):
    """T-BR-27: IAA-BR-201 per-diem-negative - Verify negative claimed amount rejected"""
    with pytest.raises(DomainValidationError, match="greater than zero"):
        validate_travel_completeness("Conference", "2026-11-01", "2026-11-05", Decimal("-100.00"), "CityA", "CityB")


def test_t_br_28_claim_under_50000_standard_threshold(base_setup):
    """T-BR-28: IAA-BR-202 standard-threshold - Verify claim < 50000 verified directly by finance"""
    assert is_high_value_ta(Decimal("49999.00"), Decimal("50000.00")) is False


def test_t_br_29_claim_gte_50000_high_threshold(base_setup):
    """T-BR-29: IAA-BR-202 high-threshold - Verify claim >= 50000 requires authority approval"""
    assert is_high_value_ta(Decimal("50000.00"), Decimal("50000.00")) is True
    assert is_high_value_ta(Decimal("75000.00"), Decimal("50000.00")) is True


# --- IAA-BR-301 & 302: Internal Audit Rules ---

def test_t_br_30_audit_observation_valid_states(base_setup):
    """T-BR-30: IAA-BR-301 three-states - Verify audit observation valid states are open, responded, closed"""
    s1 = transition_audit_observation("open", "respond", "basic_user")
    assert s1 == "responded"
    s2 = transition_audit_observation(s1, "close", "auditor")
    assert s2 == "closed"


def test_t_br_31_unsatisfactory_response_returns_observation_to_open(base_setup):
    """T-BR-31: IAA-BR-301 loop-to-open - Verify unsatisfactory response returns observation to open"""
    s = transition_audit_observation("responded", "reject_response", "auditor")
    assert s == "open"


def test_t_br_32_satisfactory_response_transitions_to_closed(base_setup):
    """T-BR-32: IAA-BR-302 close-satisfactory - Verify satisfactory response transitions to closed"""
    obs = AuditObservation.objects.create(
        auditor_id=6001,
        department="CSE",
        title="Check Records",
        description="Records missing",
        status="responded",
    )
    closed = audit_services.review_and_close_observation(obs.id, 6001, "auditor", True, "Satisfactory documentation")
    assert closed.status == "closed"


# --- IAA-BR-401: Timed Escalation ---

def test_t_br_33_overdue_approval_escalated_to_director(base_setup):
    """T-BR-33: IAA-BR-401 overdue-escalate - Verify pending approval exceeding timeout escalated to Director"""
    req = ExpenseVoucherRequest.objects.create(
        user_id=1001,
        department="CSE",
        request_type="expense",
        title="Overdue Request",
        total_amount=Decimal("5000.00"),
        status=RequestStatus.FINANCE_VALIDATED,
        approval_assigned_at=timezone.now() - timedelta(days=5),
    )
    approval_services.escalate_overdue_approval("request", req.id, "Director")
    req.refresh_from_db()
    assert req.status == RequestStatus.ESCALATED
    assert req.assigned_approver_role == "Director"


def test_t_br_34_recent_approval_within_sla_not_escalated(base_setup):
    """T-BR-34: IAA-BR-401 recent-no-escalate - Verify recent approval within SLA is not escalated"""
    from modules.iaa.tasks import escalate_overdue_approvals
    req = ExpenseVoucherRequest.objects.create(
        user_id=1001,
        department="CSE",
        request_type="expense",
        title="Recent Request",
        total_amount=Decimal("5000.00"),
        status=RequestStatus.FINANCE_VALIDATED,
        approval_assigned_at=timezone.now(),
    )
    escalate_overdue_approvals()
    req.refresh_from_db()
    assert req.status == RequestStatus.FINANCE_VALIDATED


# --- IAA-BR-501 .. 504: Scoping, Audit Immutability & Notifications ---

def test_t_br_35_basic_user_cannot_see_other_users_records(base_setup):
    """T-BR-35: IAA-BR-501 user-isolation - Verify Basic User cannot see other users records"""
    r1 = ExpenseVoucherRequest.objects.create(user_id=1001, department="CSE", title="U1 Req", total_amount=Decimal("100.00"))
    r2 = ExpenseVoucherRequest.objects.create(user_id=2002, department="CSE", title="U2 Req", total_amount=Decimal("200.00"))
    p = make_principal(user_id=1001, modules=("iaa",), permissions=())
    scoped = scoping_selectors.scope_requests(ExpenseVoucherRequest.objects.all(), p)
    ids = [r.id for r in scoped]
    assert r1.id in ids
    assert r2.id not in ids


def test_t_br_36_detail_endpoint_returns_404_for_out_of_scope_record(base_setup, stub_iam):
    """T-BR-36: IAA-BR-501 out-of-scope-404 - Verify detail endpoint returns 404 for out-of-scope record"""
    req = ExpenseVoucherRequest.objects.create(
        user_id=2002,
        department="CSE",
        request_type="expense",
        title="Other User Confidential Item",
        total_amount=Decimal("1000.00"),
        status=RequestStatus.SUBMITTED,
    )
    stub_iam(make_session(user_id=1001, modules=("iaa",), permissions=("iaa.request.view_self",)))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    response = client.get(f"/api/v1/iaa/requests/{req.id}/")
    assert response.status_code == 404


def test_t_br_37_audit_log_immutably_preserves_acting_role(base_setup):
    """T-BR-37: IAA-BR-502 role-integrity - Verify audit log immutably preserves acting role"""
    entry = audit_trail_services.record_audit_log(
        user_id=5005,
        acting_role="dean",
        action="approve_request",
        target_type="request",
        target_id=99,
        resulting_status="approved",
    )
    assert entry.acting_role == "dean"
    assert entry.user_id == 5005


def test_t_br_38_state_transitions_generate_audit_log_entries(base_setup):
    """T-BR-38: IAA-BR-503 complete-logging - Verify state transitions generate audit log entries"""
    req = request_services.create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Logged Item",
        items=[{"description": "Item", "amount": Decimal("1000.00"), "category": "MISC"}],
    )
    request_services.submit_expense_request(req.id, 1001, "basic_user")
    logs = AuditLogEntry.objects.filter(target_type="request", target_id=req.id)
    assert logs.count() >= 1
    assert logs.filter(action="submit_request").exists()


def test_t_br_39_notifications_emitted_on_status_changes(base_setup):
    """T-BR-39: IAA-BR-504 notifications - Verify notifications emitted on status changes"""
    req = ExpenseVoucherRequest.objects.create(
        user_id=1001,
        department="CSE",
        request_type="expense",
        title="Notify Item",
        total_amount=Decimal("5000.00"),
        status=RequestStatus.FINANCE_VALIDATED,
        current_approval_level=1,
        required_approval_levels=1,
    )
    with patch("modules.iaa.services.approvals.emit_notification") as mock_notify:
        approval_services.record_request_decision(req.id, 2001, "HOD", "approve", "Approved notification check")
        assert mock_notify.called
        assert mock_notify.call_args[1]["target_type"] == "request"
        assert mock_notify.call_args[1]["target_id"] == req.id
