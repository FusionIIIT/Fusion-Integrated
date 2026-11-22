"""Automated specification-based test suite for RSPC module - BR Strategy.
Generated from a8_design/BR_DESIGN.json.
Source of Truth: RSPC Problem Statement v1.0 and Business Rule Specifications v1.3.
"""
from datetime import date
from decimal import Decimal

from modules.rspc.domain.rules import (
    CLOSURE_STATUS_ARCHIVED,
    CONSULTANCY_STATUS_APPROVED_DEAN,
    CONSULTANCY_STATUS_DRAFT,
    DEAN_FINANCIAL_DELEGATION_LIMIT,
    OPERATION_PERMISSIONS,
    PROPOSAL_STATUS_APPROVED_DEAN,
    PROPOSAL_STATUS_APPROVED_DIRECTOR,
    PROPOSAL_STATUS_CHOICES,
    PROPOSAL_STATUS_DRAFT,
    PROPOSAL_STATUS_FORWARDED_DIRECTOR,
    PROPOSAL_STATUS_RECOMMENDED_HOD,
    PROPOSAL_STATUS_SUBMITTED_HOD,
    PROPOSAL_STATUS_VERIFIED_ADMIN,
    is_director_approval_required,
    validate_consultancy_project,
    validate_procurement_request,
    validate_project_closure,
    validate_research_proposal,
)
from modules.rspc.models import (
    ConsultancyProject,
    FinancialRequest,
    ProcurementRequest,
    ProgressReport,
    ProjectStaffAppointment,
    ResearchProposal,
    RSPCAuditTrail,
)
from modules.rspc.registry import ROLE_GRANTS


def test_br_001_strategic_proposal_director_routing():
    """TEST-BR-001 | BR-RSPC-004 condition-strategic
    Verify strategic research proposal escalates to Director regardless of budget.
    """
    assert is_director_approval_required("proposal", Decimal("50000.00"), is_strategic=True) is True


def test_br_002_director_approval_large_funding_threshold():
    """TEST-BR-002 | BR-RSPC-005 threshold-true
    Verify Director approval required for proposal budget >= 10 Lakhs threshold.
    """
    assert is_director_approval_required("proposal", Decimal("1000000.00")) is True


def test_br_003_director_approval_below_threshold():
    """TEST-BR-003 | BR-RSPC-005 threshold-false
    Verify Director approval not required for proposal budget < 10 Lakhs threshold.
    """
    assert is_director_approval_required("proposal", Decimal("999999.99")) is False


def test_br_004_director_authorization_high_value_expenditures():
    """TEST-BR-004 | BR-RSPC-006 threshold-true
    Verify Director authorization required for high-value expenditure >= 2 Lakhs.
    """
    assert is_director_approval_required("expenditure", Decimal("200000.00")) is True


def test_br_005_director_authorization_below_expenditure_threshold():
    """TEST-BR-005 | BR-RSPC-006 threshold-false
    Verify Director authorization not required for expenditure < 2 Lakhs.
    """
    assert is_director_approval_required("expenditure", Decimal("199999.00")) is False


def test_br_006_research_proposal_routing_sequence():
    """TEST-BR-006 | BR-RSPC-012 sequence-valid
    Verify research proposal approval route sequence statuses.
    """
    assert PROPOSAL_STATUS_DRAFT in PROPOSAL_STATUS_CHOICES
    assert PROPOSAL_STATUS_SUBMITTED_HOD in PROPOSAL_STATUS_CHOICES
    assert PROPOSAL_STATUS_RECOMMENDED_HOD in PROPOSAL_STATUS_CHOICES
    assert PROPOSAL_STATUS_VERIFIED_ADMIN in PROPOSAL_STATUS_CHOICES
    assert PROPOSAL_STATUS_APPROVED_DEAN in PROPOSAL_STATUS_CHOICES
    assert PROPOSAL_STATUS_FORWARDED_DIRECTOR in PROPOSAL_STATUS_CHOICES
    assert PROPOSAL_STATUS_APPROVED_DIRECTOR in PROPOSAL_STATUS_CHOICES


def test_br_007_proposal_mandatory_fields_validation_pass():
    """TEST-BR-007 | BR-RSPC-013 mandatory-valid
    Verify mandatory research proposal fields validation passes with all fields present.
    """
    payload = {
        "title": "Quantum Sensor Development",
        "pi_id": 101,
        "department": "Physics",
        "funding_agency": "ISRO",
        "budget": Decimal("850000.00"),
        "objectives": "Fabricate nitrogen vacancy diamond sensors",
        "start_date": date(2026, 8, 1),
        "end_date": date(2028, 7, 31),
    }
    assert validate_research_proposal(payload) == []


def test_br_008_proposal_mandatory_missing_fields():
    """TEST-BR-008 | BR-RSPC-013 mandatory-missing
    Verify proposal validation rejects missing title, pi_id, dept, agency, or objectives.
    """
    payload = {
        "title": "",
        "pi_id": None,
        "department": "",
        "funding_agency": "",
        "objectives": "",
        "budget": None,
        "start_date": None,
        "end_date": None,
    }
    errors = validate_research_proposal(payload)
    assert len(errors) >= 6


def test_br_009_proposal_timeline_duration_validation():
    """TEST-BR-009 | BR-RSPC-014 timeline-duration-positive
    Verify proposal validation enforces strictly positive timeline duration (timeline_months > 0).
    """
    payload = {
        "title": "Robotics Vision",
        "pi_id": 102,
        "department": "Mechanical",
        "funding_agency": "DRDO",
        "budget": Decimal("400000.00"),
        "objectives": "Target detection",
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 12, 31),
        "timeline_months": 0,  # Invalid zero timeline
    }
    errors = validate_research_proposal(payload)
    assert any("timeline" in e.lower() or "duration" in e.lower() for e in errors), (
        "Validation must enforce timeline_months > 0 per BR-RSPC-014"
    )


def test_br_010_timestamp_proposal_decisions():
    """TEST-BR-010 | BR-RSPC-015 timestamp-captured
    Verify review decisions capture automatic timestamp.
    """
    field = RSPCAuditTrail._meta.get_field("timestamp")
    assert field.auto_now_add is True


def test_br_011_record_proposal_decision_remarks():
    """TEST-BR-011 | BR-RSPC-016 remarks-captured
    Verify review decisions capture optional or required reviewer remarks.
    """
    trail = RSPCAuditTrail(
        entity_type="proposal",
        entity_id=1,
        actor_id=201,
        action="APPROVED_DEAN",
        remarks="Sanctioned within departmental quota.",
    )
    assert trail.remarks == "Sanctioned within departmental quota."


def test_br_012_consultancy_approval_routing_statuses():
    """TEST-BR-012 | BR-RSPC-022 routing-defined
    Verify consultancy approval routing statuses follow institutional policy.
    """
    assert CONSULTANCY_STATUS_DRAFT == "DRAFT"
    assert CONSULTANCY_STATUS_APPROVED_DEAN == "APPROVED_DEAN"


def test_br_013_consultancy_institutional_share_enforcement():
    """TEST-BR-013 | BR-RSPC-022 institutional-share-minimum
    Verify consultancy validation enforces minimum 20% institutional share.
    """
    payload = {
        "title": "Bridge Structural Audit",
        "pi_id": 105,
        "client_name": "NHAI",
        "scope_of_work": "NDT testing",
        "deliverables": "Health monitoring report",
        "total_cost": Decimal("500000.00"),
        "institutional_share": Decimal("0.00"),  # Defect: must enforce share >= 20%
    }
    errors = validate_consultancy_project(payload)
    assert any("institutional share" in e.lower() or "overhead" in e.lower() for e in errors), (
        "Consultancy validation must enforce institutional share >= 20% per BR-RSPC-022"
    )


def test_br_014_director_escalation_consultancy():
    """TEST-BR-014 | BR-RSPC-022 director-escalation-consultancy
    Verify high-value consultancy (>= 10 Lakhs) escalates to Director.
    """
    needs_dir = is_director_approval_required("consultancy", Decimal("1200000.00"))
    assert needs_dir is True, "Consultancy >= 10L must escalate to Director per BR-RSPC-022"


def test_br_015_staff_appointment_routing():
    """TEST-BR-015 | BR-RSPC-026 staff-routing
    Verify staff appointment routing through Dean and Director permissions.
    """
    assert "rspc.staff.request" in ROLE_GRANTS["faculty"]
    assert "rspc.staff.manage" in ROLE_GRANTS["rspc_admin"]
    assert "rspc.staff.manage" in ROLE_GRANTS["dean_rspc"]


def test_br_016_dean_financial_delegation_limit():
    """TEST-BR-016 | BR-RSPC-032 dean-financial-limit
    Verify Dean financial approval is strictly bounded by delegation limit (2 Lakhs).
    """
    assert Decimal("200000.00") == DEAN_FINANCIAL_DELEGATION_LIMIT


def test_br_017_financial_director_escalation():
    """TEST-BR-017 | BR-RSPC-033 financial-escalation-director
    Verify financial request >= 2 Lakhs escalates to Director.
    """
    assert is_director_approval_required("financial", Decimal("250000.00")) is True


def test_br_018_audit_financial_lifecycle_events():
    """TEST-BR-018 | BR-RSPC-034 financial-audit-logging
    Verify financial request lifecycle events are audited.
    """
    trail = RSPCAuditTrail(
        entity_type="financial",
        entity_id=5,
        actor_id=202,
        action="VERIFIED_ADMIN",
        remarks="Vouchers verified against budget allocation.",
    )
    assert trail.entity_type == "financial"
    assert trail.action == "VERIFIED_ADMIN"


def test_br_019_procurement_budget_valid():
    """TEST-BR-019 | BR-RSPC-035 procurement-budget-valid
    Verify procurement within budget passes validation.
    """
    assert validate_procurement_request(Decimal("80000.00"), Decimal("100000.00")) == []


def test_br_020_procurement_budget_exceeded():
    """TEST-BR-020 | BR-RSPC-035 procurement-budget-exceeded
    Verify procurement exceeding budget fails validation.
    """
    errors = validate_procurement_request(Decimal("120000.00"), Decimal("100000.00"))
    assert len(errors) == 1
    assert "exceeds available budget" in errors[0]


def test_br_021_procurement_approval_hierarchy():
    """TEST-BR-021 | BR-RSPC-036 procurement-approval-hierarchy
    Verify procurement approval permissions in Dean role grants.
    """
    assert "rspc.procurement.approve" in ROLE_GRANTS["dean_rspc"]


def test_br_022_reporting_schedule_enforcement():
    """TEST-BR-022 | BR-RSPC-037 progress-reporting-schedule
    Verify progress reporting model tracks period start and end dates.
    """
    rep = ProgressReport(
        project_id=1,
        submitted_by_id=101,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 6, 30),
    )
    assert rep.period_end > rep.period_start


def test_br_023_access_historical_progress_reports():
    """TEST-BR-023 | BR-RSPC-038 progress-report-access
    Verify authorized access to historical progress reports.
    """
    assert ProgressReport._meta.ordering == ["-created_at"]
    assert "rspc.report.submit" in ROLE_GRANTS["faculty"]


def test_br_024_access_historical_utilization_reports():
    """TEST-BR-024 | BR-RSPC-039 utilization-report-access
    Verify progress report captures funds utilized for compliance.
    """
    rep = ProgressReport(
        project_id=1,
        submitted_by_id=101,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 6, 30),
        funds_utilized=Decimal("150000.00"),
    )
    assert rep.funds_utilized == Decimal("150000.00")


def test_br_025_closure_archival_settlement_and_asset_constraint():
    """TEST-BR-025 | BR-RSPC-043 closure-archival-constraints
    Verify project closure rejects archival when financial settlement is pending.
    """
    errors = validate_project_closure(financial_settled=False, has_asset_declaration=True)
    assert len(errors) == 1
    assert "financial settlement is pending" in errors[0]


def test_br_026_integration_configured_boundaries():
    """TEST-BR-026 | BR-RSPC-045 integration-explicit-only
    Verify RSPC module does not declare cross-module ForeignKeys (ADR-0013).
    """
    for model in [ResearchProposal, ConsultancyProject, ProjectStaffAppointment, FinancialRequest, ProcurementRequest]:
        for field in model._meta.fields:
            assert not field.is_relation or field.many_to_one is False, f"Unexpected relation on {model}.{field.name}"


def test_br_027_role_based_access_data():
    """TEST-BR-027 | BR-RSPC-048 rbac-enforcement
    Verify role-based access control maps operations to permissions.
    """
    assert len(OPERATION_PERMISSIONS) == 22


def test_br_028_actions_restricted_by_role():
    """TEST-BR-028 | BR-RSPC-049 actions-restricted-by-role
    Verify faculty cannot approve proposals or financial requests.
    """
    faculty_perms = ROLE_GRANTS["faculty"]
    assert "rspc.proposal.approve_dean" not in faculty_perms
    assert "rspc.financial.approve_dean" not in faculty_perms


def test_br_029_maintain_audit_compliance_logs():
    """TEST-BR-029 | BR-RSPC-050 audit-compliance-logging
    Verify structured audit trail table exists and stores required fields.
    """
    assert RSPCAuditTrail._meta.db_table == "rspc_audit_trail"


def test_br_030_boundary_no_payroll_execution():
    """TEST-BR-030 | BR-RSPC-058 boundary-no-payroll
    Verify staff model does not perform payroll execution.
    """
    staff_fields = [f.name for f in ProjectStaffAppointment._meta.get_fields()]
    assert "bank_account" not in staff_fields
    assert "salary_disbursement_date" not in staff_fields


def test_br_031_boundary_no_bank_payment_execution():
    """TEST-BR-031 | BR-RSPC-059 boundary-no-bank-payment
    Verify financial request does not process banking transactions.
    """
    fin_fields = [f.name for f in FinancialRequest._meta.get_fields()]
    assert "bank_account_number" not in fin_fields


def test_br_032_boundary_no_inventory_execution():
    """TEST-BR-032 | BR-RSPC-060 boundary-no-inventory-execution
    Verify procurement request does not manage physical warehouse bins.
    """
    proc_fields = [f.name for f in ProcurementRequest._meta.get_fields()]
    assert "bin_location" not in proc_fields


def test_br_033_lifecycle_permitted_updates_constraint():
    """TEST-BR-033 | BR-RSPC-065 lifecycle-permitted-updates
    Verify project updates are restricted to valid active lifecycle states.
    """
    assert CLOSURE_STATUS_ARCHIVED == "ARCHIVED"
    import modules.rspc.domain.rules as rules
    assert hasattr(rules, "can_update_project"), "can_update_project check required per BR-RSPC-065"
