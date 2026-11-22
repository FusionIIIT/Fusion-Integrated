"""Automated specification-based test suite for RSPC module - UC Strategy.
Generated from a8_design/UC_DESIGN.json.
Source of Truth: RSPC Problem Statement v1.0 and Use Case Specifications v1.3.
"""
from datetime import date
from decimal import Decimal

from modules.rspc.contracts import (
    ConsultancyProjectContract,
    RSPCProjectSummaryContract,
)
from modules.rspc.domain.rules import (
    CLOSURE_STATUS_APPROVED_DEAN,
    CLOSURE_STATUS_ARCHIVED,
    CLOSURE_STATUS_VERIFIED_ADMIN,
    FINANCIAL_STATUS_APPROVED_DEAN,
    FINANCIAL_STATUS_ESCALATED_DIRECTOR,
    FINANCIAL_STATUS_VERIFIED_ADMIN,
    PROPOSAL_STATUS_APPROVED_DEAN,
    PROPOSAL_STATUS_APPROVED_DIRECTOR,
    PROPOSAL_STATUS_DRAFT,
    PROPOSAL_STATUS_FORWARDED_DIRECTOR,
    PROPOSAL_STATUS_RECOMMENDED_HOD,
    PROPOSAL_STATUS_REJECTED_ADMIN,
    PROPOSAL_STATUS_REJECTED_HOD,
    PROPOSAL_STATUS_VERIFIED_ADMIN,
    is_director_approval_required,
    validate_consultancy_project,
    validate_financial_request,
    validate_procurement_request,
    validate_project_closure,
    validate_research_proposal,
)
from modules.rspc.models import (
    ProgressReport,
    ProjectStaffAppointment,
    ResearchProposal,
    RSPCAuditTrail,
    RSPCNotification,
)
from modules.rspc.registry import ROLE_GRANTS


def test_uc_001_view_own_portfolio():
    """TEST-UC-001 | RSPC-UC-001 Main Flow
    Faculty views own RSPC project portfolio.
    """
    summary = RSPCProjectSummaryContract(
        project_id=1,
        project_type="research",
        title="Edge Computing Testbed",
        pi_id=101,
        total_sanctioned_budget=Decimal("1200000.00"),
        status=PROPOSAL_STATUS_APPROVED_DEAN,
    )
    assert summary.project_id == 1
    assert summary.pi_id == 101
    assert "rspc.proposal.view" in ROLE_GRANTS["faculty"]


def test_uc_002_submit_research_proposal():
    """TEST-UC-002 | RSPC-UC-002 Main Flow
    Faculty submits research project proposal with complete valid details.
    """
    payload = {
        "title": "Machine Learning for Healthcare Diagnostics",
        "pi_id": 105,
        "department": "Biomedical Engineering",
        "funding_agency": "ICMR",
        "budget": Decimal("2200000.00"),
        "objectives": "Develop deep neural networks for early cancer detection",
        "start_date": date(2026, 9, 1),
        "end_date": date(2029, 8, 31),
        "timeline_months": 36,
    }
    errors = validate_research_proposal(payload)
    assert errors == []


def test_uc_003_save_proposal_draft():
    """TEST-UC-003 | RSPC-UC-002 Alternative A1
    Save research proposal as draft for subsequent completion.
    """
    proposal = ResearchProposal(
        title="Draft Smart Grid Study",
        pi_id=102,
        department="Electrical Engineering",
        funding_agency="CPRI",
        budget=Decimal("500000.00"),
        objectives="Pending finalization",
        start_date=date(2026, 6, 1),
        end_date=date(2027, 5, 31),
        status=PROPOSAL_STATUS_DRAFT,
    )
    assert proposal.status == "DRAFT"


def test_uc_004_proposal_submission_validation_exception():
    """TEST-UC-004 | RSPC-UC-002 Exception E1
    Proposal submission fails validation due to non-positive timeline or invalid budget.
    """
    invalid_payload = {
        "title": "Invalid Proposal",
        "pi_id": 101,
        "department": "CSE",
        "funding_agency": "DST",
        "budget": Decimal("-1000.00"),
        "objectives": "Study",
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 12, 31),
        "timeline_months": 0,  # Invalid zero timeline
    }
    errors = validate_research_proposal(invalid_payload)
    assert any("budget" in e.lower() for e in errors), "Budget error required"
    assert any("timeline" in e.lower() or "duration" in e.lower() for e in errors), "Timeline error required per UC-002 E1"


def test_uc_005_hod_recommend_proposal():
    """TEST-UC-005 | RSPC-UC-003 Main Flow
    HoD reviews and recommends research proposal.
    """
    assert "rspc.proposal.recommend_hod" in ROLE_GRANTS["hod"]
    assert PROPOSAL_STATUS_RECOMMENDED_HOD == "RECOMMENDED_HOD"


def test_uc_006_hod_reject_proposal():
    """TEST-UC-006 | RSPC-UC-003 Alternative A1
    HoD reviews and rejects research proposal with remarks.
    """
    assert PROPOSAL_STATUS_REJECTED_HOD == "REJECTED_HOD"
    trail = RSPCAuditTrail(
        entity_type="proposal",
        entity_id=12,
        actor_id=50,
        action="REJECT_HOD",
        remarks="Insufficient departmental laboratory facilities for proposed work.",
    )
    assert trail.remarks != ""


def test_uc_007_admin_verify_proposal():
    """TEST-UC-007 | RSPC-UC-004 Main Flow
    RSPC Admin verifies proposal completeness and regulatory compliance.
    """
    assert "rspc.proposal.verify_admin" in ROLE_GRANTS["rspc_admin"]
    assert PROPOSAL_STATUS_VERIFIED_ADMIN == "VERIFIED_ADMIN"


def test_uc_008_admin_reject_proposal():
    """TEST-UC-008 | RSPC-UC-004 Alternative A1
    RSPC Admin rejects proposal as not eligible with remarks.
    """
    assert PROPOSAL_STATUS_REJECTED_ADMIN == "REJECTED_ADMIN"


def test_uc_009_dean_approve_proposal():
    """TEST-UC-009 | RSPC-UC-005 Main Flow
    Dean-RSPC approves proposal within delegated powers.
    """
    assert "rspc.proposal.approve_dean" in ROLE_GRANTS["dean_rspc"]
    assert PROPOSAL_STATUS_APPROVED_DEAN == "APPROVED_DEAN"


def test_uc_010_dean_forward_to_director():
    """TEST-UC-010 | RSPC-UC-005 Alternative A1
    Dean-RSPC forwards large funding proposal to Director.
    """
    needs_dir = is_director_approval_required("proposal", Decimal("1500000.00"))
    assert needs_dir is True
    assert PROPOSAL_STATUS_FORWARDED_DIRECTOR == "FORWARDED_DIRECTOR"


def test_uc_011_director_authorize_proposal():
    """TEST-UC-011 | RSPC-UC-006 Main Flow
    Director reviews and authorizes significant proposal.
    """
    assert "rspc.proposal.authorize_director" in ROLE_GRANTS["director"]
    assert PROPOSAL_STATUS_APPROVED_DIRECTOR == "APPROVED_DIRECTOR"


def test_uc_012_register_consultancy():
    """TEST-UC-012 | RSPC-UC-007 Main Flow
    Faculty registers consultancy project with complete details.
    """
    payload = {
        "title": "Industrial Automation Consultancy",
        "pi_id": 103,
        "client_name": "Tata Motors Ltd.",
        "scope_of_work": "PLC programming and robotics integration",
        "deliverables": "Operational software and maintenance manual",
        "total_cost": Decimal("800000.00"),
    }
    errors = validate_consultancy_project(payload)
    assert errors == []


def test_uc_013_consultancy_invalid_cost_exception():
    """TEST-UC-013 | RSPC-UC-007 Exception E1
    Consultancy registration rejected when mandatory financial terms or institutional share are invalid.
    """
    payload = {
        "title": "Zero Cost Consultancy",
        "pi_id": 103,
        "client_name": "Client Y",
        "scope_of_work": "Consulting",
        "deliverables": "Notes",
        "total_cost": Decimal("0.00"),
        "institutional_share": Decimal("0.00"),  # Defect: must enforce share >= 20%
    }
    errors = validate_consultancy_project(payload)
    assert any("cost" in e.lower() for e in errors), "Cost validation error required"
    assert any("institutional share" in e.lower() or "overhead" in e.lower() for e in errors), (
        "Institutional share validation error required per UC-007 E2"
    )


def test_uc_014_track_consultancy_deliverables():
    """TEST-UC-014 | RSPC-UC-008 Main Flow
    Faculty tracks consultancy deliverables and financial terms.
    """
    contract = ConsultancyProjectContract(
        id=5,
        title="Power System Audit",
        pi_id=103,
        client_name="NTPC",
        total_cost=Decimal("600000.00"),
        institutional_share=Decimal("120000.00"),
        status="APPROVED_DEAN",
        start_date="2026-05-01",
        end_date="2026-11-30",
    )
    assert contract.institutional_share == Decimal("120000.00")
    assert contract.client_name == "NTPC"


def test_uc_015_request_staff_appointment():
    """TEST-UC-015 | RSPC-UC-009 Main Flow
    Faculty requests project-based staff appointment.
    """
    staff = ProjectStaffAppointment(
        project_id=1,
        pi_id=101,
        position_title="Research Associate (RA)",
        stipend_amount=Decimal("47000.00"),
        duration_months=24,
        status="REQUESTED",
    )
    assert staff.position_title == "Research Associate (RA)"
    assert staff.status == "REQUESTED"


def test_uc_016_admin_manage_staff_records():
    """TEST-UC-016 | RSPC-UC-010 Main Flow
    RSPC Admin verifies and manages staff appointment operational records.
    """
    assert "rspc.staff.manage" in ROLE_GRANTS["rspc_admin"]


def test_uc_017_submit_financial_request():
    """TEST-UC-017 | RSPC-UC-011 Main Flow
    Faculty submits fund utilization or expenditure request.
    """
    errors = validate_financial_request(
        amount=Decimal("30000.00"),
        available_budget=Decimal("50000.00"),
    )
    assert errors == []


def test_uc_018_financial_request_exceeds_budget_exception():
    """TEST-UC-018 | RSPC-UC-011 Exception E1
    Financial request rejected when requested amount exceeds available budget.
    """
    errors = validate_financial_request(
        amount=Decimal("75000.00"),
        available_budget=Decimal("50000.00"),
    )
    assert len(errors) > 0
    assert "exceeds available sanctioned budget" in errors[0]


def test_uc_019_admin_verify_financial_request():
    """TEST-UC-019 | RSPC-UC-012 Main Flow
    RSPC Admin verifies financial request and forwards for approval.
    """
    assert "rspc.financial.verify" in ROLE_GRANTS["rspc_admin"]
    assert FINANCIAL_STATUS_VERIFIED_ADMIN == "VERIFIED_ADMIN"


def test_uc_020_request_procurement():
    """TEST-UC-020 | RSPC-UC-013 Main Flow
    Faculty requests equipment or consumable procurement.
    """
    errors = validate_procurement_request(
        estimated_cost=Decimal("150000.00"),
        available_budget=Decimal("200000.00"),
    )
    assert errors == []


def test_uc_021_procurement_exceeds_budget_exception():
    """TEST-UC-021 | RSPC-UC-013 Exception E1
    Procurement request rejected when cost exceeds available equipment budget.
    """
    errors = validate_procurement_request(
        estimated_cost=Decimal("250000.00"),
        available_budget=Decimal("200000.00"),
    )
    assert len(errors) > 0
    assert "exceeds available budget" in errors[0]


def test_uc_022_submit_progress_report():
    """TEST-UC-022 | RSPC-UC-014 Main Flow
    Faculty submits periodic progress and utilization report.
    """
    rep = ProgressReport(
        project_id=2,
        submitted_by_id=102,
        report_type="quarterly",
        period_start=date(2026, 4, 1),
        period_end=date(2026, 6, 30),
        summary="Quarter 1 work completed",
        funds_utilized=Decimal("75000.00"),
        status="SUBMITTED",
    )
    assert rep.status == "SUBMITTED"
    assert rep.funds_utilized == Decimal("75000.00")


def test_uc_023_submit_project_closure():
    """TEST-UC-023 | RSPC-UC-015 Main Flow
    Faculty submits project closure and completion report.
    """
    errors = validate_project_closure(
        financial_settled=True,
        has_asset_declaration=True,
    )
    assert errors == []


def test_uc_024_project_closure_unsettled_exception():
    """TEST-UC-024 | RSPC-UC-015 Exception E1
    Project closure rejected when financial liabilities are unsettled.
    """
    errors = validate_project_closure(
        financial_settled=False,
        has_asset_declaration=True,
    )
    assert len(errors) == 1
    assert "financial settlement is pending" in errors[0]


def test_uc_025_receive_view_notifications():
    """TEST-UC-025 | RSPC-UC-016 Main Flow
    Authorized user receives and views RSPC notifications.
    """
    notif = RSPCNotification(
        recipient_id=101,
        event_type="FINANCIAL_APPROVED",
        title="Expenditure Request Approved",
        message="Your request for Consumables (Rs. 45000) was approved.",
    )
    assert notif.is_read is False


def test_uc_026_admin_review_audit_logs():
    """TEST-UC-026 | RSPC-UC-017 Main Flow
    RSPC Admin reviews audit logs and compliance records.
    """
    assert "rspc.audit.view" in ROLE_GRANTS["rspc_admin"]


def test_uc_027_synchronize_role_assignment():
    """TEST-UC-027 | RSPC-UC-018 Main Flow
    Synchronize RSPC role assignment change from IAM.
    """
    audit = RSPCAuditTrail(
        entity_type="iam_role",
        entity_id=105,
        actor_id=1,
        action="ROLE_ASSIGNED",
        remarks="Assigned hod role to user 105",
    )
    assert audit.action == "ROLE_ASSIGNED"


def test_uc_028_update_project_lifecycle_info():
    """TEST-UC-028 | RSPC-UC-021 Main Flow
    Faculty updates project lifecycle information in active state.
    """
    proposal = ResearchProposal(
        title="Cyber-physical Systems Research",
        pi_id=104,
        status="APPROVED_DEAN",
    )
    assert proposal.status == "APPROVED_DEAN"


def test_uc_029_update_blocked_on_archived_exception():
    """TEST-UC-029 | RSPC-UC-021 Exception E1
    Project lifecycle update blocked when project is archived or closed.
    """
    assert CLOSURE_STATUS_ARCHIVED == "ARCHIVED"
    import modules.rspc.domain.rules as rules
    assert hasattr(rules, "can_update_project"), "can_update_project check required per UC-021 E1"


def test_uc_030_record_staff_selection_recommendation():
    """TEST-UC-030 | RSPC-UC-022 Main Flow
    Faculty records staff selection recommendation.
    """
    staff = ProjectStaffAppointment(
        project_id=1,
        pi_id=101,
        selected_candidate_name="Alice Smith",
    )
    assert staff.selected_candidate_name == "Alice Smith"


def test_uc_031_dean_review_staff_appointment():
    """TEST-UC-031 | RSPC-UC-023 Main Flow
    Dean-RSPC reviews and decides staff appointment request.
    """
    assert "rspc.staff.manage" in ROLE_GRANTS["dean_rspc"]


def test_uc_032_dean_approve_financial_request():
    """TEST-UC-032 | RSPC-UC-024 Main Flow
    Dean-RSPC reviews and approves financial request within delegation.
    """
    assert FINANCIAL_STATUS_APPROVED_DEAN == "APPROVED_DEAN"
    assert "rspc.financial.approve_dean" in ROLE_GRANTS["dean_rspc"]


def test_uc_033_financial_request_escalate_to_director():
    """TEST-UC-033 | RSPC-UC-024 Alternative A1
    Financial request exceeds Dean limit and is escalated to Director.
    """
    needs_dir = is_director_approval_required("financial", Decimal("300000.00"))
    assert needs_dir is True
    assert FINANCIAL_STATUS_ESCALATED_DIRECTOR == "ESCALATED_DIRECTOR"


def test_uc_034_admin_verify_procurement():
    """TEST-UC-034 | RSPC-UC-025 Main Flow
    RSPC Admin verifies procurement request against sanctioned budget.
    """
    errors = validate_procurement_request(Decimal("100000.00"), Decimal("150000.00"))
    assert errors == []


def test_uc_035_dean_approve_procurement():
    """TEST-UC-035 | RSPC-UC-026 Main Flow
    Dean-RSPC approves procurement request.
    """
    assert "rspc.procurement.approve" in ROLE_GRANTS["dean_rspc"]


def test_uc_036_admin_verify_closure():
    """TEST-UC-036 | RSPC-UC-027 Main Flow
    RSPC Admin verifies project closure and asset records.
    """
    assert CLOSURE_STATUS_VERIFIED_ADMIN == "VERIFIED_ADMIN"


def test_uc_037_dean_approve_closure():
    """TEST-UC-037 | RSPC-UC-028 Main Flow
    Dean-RSPC approves project closure and triggers archival.
    """
    assert CLOSURE_STATUS_APPROVED_DEAN == "APPROVED_DEAN"
    assert CLOSURE_STATUS_ARCHIVED == "ARCHIVED"


def test_uc_038_exchange_integration_records():
    """TEST-UC-038 | RSPC-UC-029 Main Flow
    Exchange RSPC integration records across Fusion modules.
    """
    contract = RSPCProjectSummaryContract(
        project_id=10,
        project_type="consultancy",
        title="Highway Bridge Assessment",
        pi_id=106,
        total_sanctioned_budget=Decimal("500000.00"),
        status="APPROVED_DEAN",
    )
    assert contract.project_type == "consultancy"
    assert contract.total_sanctioned_budget == Decimal("500000.00")


def test_uc_039_record_external_funding_tracking():
    """TEST-UC-039 | RSPC-UC-030 Main Flow
    Record external funding-agency tracking update.
    """
    p = ResearchProposal(
        title="Solar Cell Efficiency Study",
        funding_agency="MNRE",
        scheme_name="National Solar Mission Phase II",
        pi_id=107,
    )
    assert p.scheme_name == "National Solar Mission Phase II"


def test_uc_040_system_event_notification():
    """TEST-UC-040 | RSPC-UC-031 Main Flow
    Generate and dispatch system notification on lifecycle events.
    """
    notif = RSPCNotification(
        recipient_id=105,
        event_type="CLOSURE_ARCHIVED",
        title="Project Archived",
        message="Project has been successfully archived.",
    )
    assert notif.event_type == "CLOSURE_ARCHIVED"
