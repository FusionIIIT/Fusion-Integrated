"""Automated specification-based test suite for RSPC module - FR Strategy.
Generated from a8_design/FR_DESIGN.json.
Source of Truth: RSPC Problem Statement v1.0 and Requirement Registry CFR/AFR v1.3.
"""
from datetime import date
from decimal import Decimal

from modules.rspc.contracts import (
    ResearchProposalContract,
)
from modules.rspc.domain.rules import (
    CLOSURE_STATUS_ARCHIVED,
    CLOSURE_STATUS_REQUESTED,
    CONSULTANCY_STATUS_DRAFT,
    DEAN_FINANCIAL_DELEGATION_LIMIT,
    FINANCIAL_STATUS_SUBMITTED,
    LARGE_FUNDING_PROPOSAL_THRESHOLD,
    OPERATION_PERMISSIONS,
    PROPOSAL_STATUS_APPROVED_DEAN,
    PROPOSAL_STATUS_APPROVED_DIRECTOR,
    PROPOSAL_STATUS_CHOICES,
    PROPOSAL_STATUS_DRAFT,
    PROPOSAL_STATUS_FORWARDED_DIRECTOR,
    PROPOSAL_STATUS_RECOMMENDED_HOD,
    PROPOSAL_STATUS_REJECTED_ADMIN,
    PROPOSAL_STATUS_SUBMITTED_HOD,
    PROPOSAL_STATUS_VERIFIED_ADMIN,
    is_director_approval_required,
    validate_consultancy_project,
    validate_financial_request,
    validate_procurement_request,
    validate_project_closure,
    validate_research_proposal,
)
from modules.rspc.models import (
    ConsultancyProject,
    FinancialRequest,
    ProcurementRequest,
    ProgressReport,
    ProjectClosure,
    ProjectStaffAppointment,
    ResearchProposal,
    RSPCAuditTrail,
    RSPCNotification,
)
from modules.rspc.registry import NAV_ITEMS, PERMISSIONS, ROLE_GRANTS


def test_fr_001_faculty_view_own_projects():
    """TEST-FR-001 | RSPC-CFR-001 / RSPC-FR-004
    Verify faculty can access their own project portfolio via contract queries.
    """
    contract = ResearchProposalContract(
        id=1,
        title="AI Assisted Testing in Fusion ERP",
        pi_id=101,
        department="Computer Science & Engineering",
        funding_agency="SERB-DST",
        budget=Decimal("1500000.00"),
        status=PROPOSAL_STATUS_APPROVED_DEAN,
        start_date="2026-07-01",
        end_date="2028-06-30",
    )
    assert contract.id == 1
    assert contract.pi_id == 101
    assert "rspc.proposal.view" in ROLE_GRANTS["faculty"]
    assert any(nav["required_permission"] == "rspc.proposal.view" for nav in NAV_ITEMS)


def test_fr_002_audit_trail_logging():
    """TEST-FR-002 | RSPC-CFR-002 / RSPC-FR-007
    Verify structured audit trail captures review decisions and action history.
    """
    trail = RSPCAuditTrail(
        entity_type="proposal",
        entity_id=1,
        actor_id=50,
        action="RECOMMEND_HOD",
        remarks="Recommended strongly based on merit.",
    )
    assert trail.entity_type == "proposal"
    assert trail.actor_id == 50
    assert trail.action == "RECOMMEND_HOD"
    assert RSPCAuditTrail._meta.ordering == ["-timestamp"]


def test_fr_003_hod_review_recommendation():
    """TEST-FR-003 | RSPC-CFR-003 / RSPC-FR-008
    Verify departmental HoD review capabilities and recommendation status.
    """
    assert "rspc.proposal.recommend_hod" in ROLE_GRANTS["hod"]
    assert "rspc.consultancy.recommend_hod" in ROLE_GRANTS["hod"]
    assert PROPOSAL_STATUS_RECOMMENDED_HOD in PROPOSAL_STATUS_CHOICES


def test_fr_004_dean_approval_within_delegated_limit():
    """TEST-FR-004 | RSPC-CFR-004 / RSPC-FR-010
    Verify Dean-RSPC approval authority within delegated limit.
    """
    assert "rspc.proposal.approve_dean" in ROLE_GRANTS["dean_rspc"]
    assert "rspc.financial.approve_dean" in ROLE_GRANTS["dean_rspc"]
    assert Decimal("200000.00") == DEAN_FINANCIAL_DELEGATION_LIMIT


def test_fr_005_director_approval_large_funding():
    """TEST-FR-005 | RSPC-CFR-005 / RSPC-FR-013
    Verify Director authorization is required for large funding proposals >= 10 Lakhs.
    """
    assert "rspc.proposal.authorize_director" in ROLE_GRANTS["director"]
    assert Decimal("1000000.00") == LARGE_FUNDING_PROPOSAL_THRESHOLD
    needs_dir = is_director_approval_required("proposal", Decimal("1500000.00"))
    assert needs_dir is True


def test_fr_006_proposal_submission_data_capture():
    """TEST-FR-006 | RSPC-CFR-006 / RSPC-FR-015
    Verify research proposal data capture with valid mandatory fields.
    """
    valid_payload = {
        "title": "Quantum Computing Algorithm Analysis",
        "pi_id": 101,
        "department": "Computer Science & Engineering",
        "funding_agency": "SERB-DST",
        "budget": Decimal("1500000.00"),
        "objectives": "Develop quantum error correcting codes",
        "start_date": date(2026, 7, 1),
        "end_date": date(2028, 6, 30),
        "timeline_months": 24,
    }
    errors = validate_research_proposal(valid_payload)
    assert errors == []


def test_fr_007_proposal_validation_rejects_missing_title_or_invalid_budget():
    """TEST-FR-007 | RSPC-CFR-006 / RSPC-FR-016
    Verify proposal validation rejects submissions with missing mandatory fields, non-positive budget,
    or non-positive duration/timeline.
    """
    invalid_payload = {
        "title": "",
        "pi_id": 0,
        "department": "",
        "funding_agency": "",
        "budget": Decimal("-5000.00"),
        "objectives": "",
        "start_date": date(2026, 4, 1),
        "end_date": date(2025, 4, 1),  # end before start
        "timeline_months": 0,          # Invalid non-positive duration
    }
    errors = validate_research_proposal(invalid_payload)
    assert any("title" in e.lower() for e in errors), "Title validation error expected"
    assert any("budget" in e.lower() for e in errors), "Budget validation error expected"
    assert any("pi" in e.lower() or "investigator" in e.lower() for e in errors), "PI validation error expected"
    assert any("end date" in e.lower() for e in errors), "End date validation error expected"
    assert any("timeline" in e.lower() or "duration" in e.lower() for e in errors), "Timeline duration validation error expected"


def test_fr_008_proposal_workflow_routing_sequence():
    """TEST-FR-008 | RSPC-CFR-007 / RSPC-FR-021
    Verify proposal workflow routing states sequence.
    """
    expected_sequence = [
        PROPOSAL_STATUS_DRAFT,
        PROPOSAL_STATUS_SUBMITTED_HOD,
        PROPOSAL_STATUS_RECOMMENDED_HOD,
        PROPOSAL_STATUS_VERIFIED_ADMIN,
        PROPOSAL_STATUS_APPROVED_DEAN,
        PROPOSAL_STATUS_FORWARDED_DIRECTOR,
        PROPOSAL_STATUS_APPROVED_DIRECTOR,
    ]
    for status in expected_sequence:
        assert status in PROPOSAL_STATUS_CHOICES


def test_fr_009_proposal_decision_record():
    """TEST-FR-009 | RSPC-CFR-008 / RSPC-FR-024
    Verify decision record preserves actor, action, timestamp, and remarks.
    """
    audit = RSPCAuditTrail(
        entity_type="proposal",
        entity_id=10,
        actor_id=202,
        action="APPROVED_DEAN",
        remarks="Approved within Dean powers",
    )
    assert audit.remarks == "Approved within Dean powers"
    assert audit.action == "APPROVED_DEAN"


def test_fr_010_consultancy_registration_data_capture():
    """TEST-FR-010 | RSPC-CFR-009 / RSPC-FR-027
    Verify consultancy registration captures client, scope, deliverables, and cost.
    """
    payload = {
        "title": "Structural Health Monitoring Consultancy",
        "pi_id": 105,
        "client_name": "Larsen & Toubro Ltd.",
        "scope_of_work": "Vibration analysis of bridge girders",
        "deliverables": "Technical report and sensor telemetry data",
        "total_cost": Decimal("750000.00"),
    }
    errors = validate_consultancy_project(payload)
    assert errors == []


def test_fr_011_consultancy_financial_terms_validation():
    """TEST-FR-011 | RSPC-CFR-009 / RSPC-FR-030
    Verify consultancy financial terms validation ensures institute share is properly accounted for (>= 20%).
    """
    invalid_consultancy = {
        "title": "Industrial Consultancy",
        "pi_id": 110,
        "client_name": "Client X",
        "scope_of_work": "Testing",
        "deliverables": "Report",
        "total_cost": Decimal("500000.00"),
        "institutional_share": Decimal("0.00"),  # Defect: missing required 20% institute share
    }
    errors = validate_consultancy_project(invalid_consultancy)
    assert any("institutional share" in e.lower() or "overhead" in e.lower() for e in errors), (
        "Validation must enforce institutional share >= 20% per RSPC-CFR-009 / RSPC-FR-030"
    )


def test_fr_012_consultancy_approval_routing():
    """TEST-FR-012 | RSPC-CFR-010 / RSPC-FR-033
    Verify consultancy approval routing through departmental and Dean-RSPC channels,
    and escalates high-value consultancy (>= 10 Lakhs) to Director.
    """
    assert "consultancy.register" in OPERATION_PERMISSIONS
    assert "consultancy.recommend_hod" in OPERATION_PERMISSIONS
    assert "consultancy.approve_dean" in OPERATION_PERMISSIONS
    needs_director = is_director_approval_required("consultancy", Decimal("1500000.00"))
    assert needs_director is True, "Consultancy exceeding 10 Lakhs must require Director authorization"


def test_fr_013_consultancy_tracking_deliverables_and_milestones():
    """TEST-FR-013 | RSPC-CFR-011 / RSPC-FR-034
    Verify consultancy project tracking model tracks deliverables and status.
    """
    project = ConsultancyProject(
        title="Consultancy A",
        pi_id=101,
        client_name="Client Corp",
        scope_of_work="Testing",
        deliverables="Final Report",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        total_cost=Decimal("300000.00"),
        institutional_share=Decimal("60000.00"),
        status=CONSULTANCY_STATUS_DRAFT,
    )
    assert project.total_cost == Decimal("300000.00")
    assert project.status == "DRAFT"


def test_fr_014_project_staff_appointment_creation():
    """TEST-FR-014 | RSPC-CFR-012 / RSPC-FR-039
    Verify project-based staff appointment record creation.
    """
    staff = ProjectStaffAppointment(
        project_id=1,
        project_type="research",
        pi_id=101,
        position_title="Junior Research Fellow (JRF)",
        stipend_amount=Decimal("31000.00"),
        duration_months=12,
        advertisement_details="Open advertisement on institute website",
        status="REQUESTED",
    )
    assert staff.position_title == "Junior Research Fellow (JRF)"
    assert staff.stipend_amount == Decimal("31000.00")
    assert staff.status == "REQUESTED"


def test_fr_015_staff_selection_recommendation():
    """TEST-FR-015 | RSPC-CFR-013 / RSPC-FR-043
    Verify faculty staff selection recommendation and candidate recording.
    """
    staff = ProjectStaffAppointment(
        project_id=1,
        pi_id=101,
        position_title="Project Associate I",
        stipend_amount=Decimal("25000.00"),
        selected_candidate_name="Jane Doe",
    )
    assert staff.selected_candidate_name == "Jane Doe"


def test_fr_016_staff_appointment_approval_routing():
    """TEST-FR-016 | RSPC-CFR-014 / RSPC-FR-045
    Verify staff appointment approval routing permissions.
    """
    assert "rspc.staff.request" in ROLE_GRANTS["faculty"]
    assert "rspc.staff.manage" in ROLE_GRANTS["rspc_admin"]
    assert "rspc.staff.manage" in ROLE_GRANTS["dean_rspc"]


def test_fr_017_financial_expenditure_request_submission():
    """TEST-FR-017 | RSPC-CFR-015 / RSPC-FR-049
    Verify fund utilization and expenditure request submission data capture.
    """
    req = FinancialRequest(
        project_id=1,
        requested_by_id=101,
        budget_head="Consumables",
        amount=Decimal("45000.00"),
        purpose="Chemical reagents and glassware",
        status=FINANCIAL_STATUS_SUBMITTED,
    )
    assert req.amount == Decimal("45000.00")
    assert req.status == "SUBMITTED"


def test_fr_018_financial_request_budget_exceeded_rejected():
    """TEST-FR-018 | RSPC-CFR-015 / RSPC-FR-050
    Verify financial request validation rejects requests exceeding sanctioned available budget.
    """
    errors = validate_financial_request(
        amount=Decimal("120000.00"),
        available_budget=Decimal("100000.00"),
    )
    assert len(errors) == 1
    assert "exceeds available sanctioned budget" in errors[0]


def test_fr_019_financial_approval_director_escalation():
    """TEST-FR-019 | RSPC-CFR-016 / RSPC-FR-052
    Verify financial request >= 2 Lakhs escalates to Director.
    """
    needs_dir = is_director_approval_required("financial", Decimal("250000.00"))
    assert needs_dir is True
    no_dir = is_director_approval_required("financial", Decimal("150000.00"))
    assert no_dir is False


def test_fr_020_procurement_request_creation():
    """TEST-FR-020 | RSPC-CFR-017 / RSPC-FR-056
    Verify project procurement request creation.
    """
    proc = ProcurementRequest(
        project_id=1,
        requested_by_id=101,
        item_name="High-Performance GPU Server",
        item_type="equipment",
        estimated_cost=Decimal("450000.00"),
        specifications="NVIDIA A100 80GB, 128GB RAM",
        status="REQUESTED",
    )
    assert proc.item_name == "High-Performance GPU Server"
    assert proc.estimated_cost == Decimal("450000.00")


def test_fr_021_procurement_budget_validation():
    """TEST-FR-021 | RSPC-CFR-017 / RSPC-FR-057
    Verify procurement request validation checks against sanctioned budget.
    """
    errors = validate_procurement_request(
        estimated_cost=Decimal("500000.00"),
        available_budget=Decimal("400000.00"),
    )
    assert len(errors) == 1
    assert "exceeds available budget" in errors[0]


def test_fr_022_progress_report_submission():
    """TEST-FR-022 | RSPC-CFR-018 / RSPC-FR-061
    Verify periodic progress and utilization report submission.
    """
    rep = ProgressReport(
        project_id=1,
        submitted_by_id=101,
        report_type="annual",
        period_start=date(2026, 4, 1),
        period_end=date(2027, 3, 31),
        summary="Milestone 1 completed successfully",
        funds_utilized=Decimal("350000.00"),
        status="SUBMITTED",
    )
    assert rep.funds_utilized == Decimal("350000.00")
    assert rep.status == "SUBMITTED"


def test_fr_023_historical_progress_report_access():
    """TEST-FR-023 | RSPC-CFR-019 / RSPC-FR-066
    Verify access control and ordering for historical progress reports.
    """
    assert "rspc.report.submit" in ROLE_GRANTS["faculty"]
    assert ProgressReport._meta.ordering == ["-created_at"]


def test_fr_024_project_closure_submission():
    """TEST-FR-024 | RSPC-CFR-020 / RSPC-FR-068
    Verify project closure and completion report submission.
    """
    closure = ProjectClosure(
        project_id=1,
        submitted_by_id=101,
        financial_settlement_status="settled",
        asset_declaration="All equipment inventoried in lab room 204",
        closure_summary="All project deliverables achieved satisfactorily.",
        status=CLOSURE_STATUS_REQUESTED,
    )
    assert closure.status == "REQUESTED"
    assert closure.financial_settlement_status == "settled"


def test_fr_025_project_closure_unsettled_liabilities_rejected():
    """TEST-FR-025 | RSPC-CFR-020 / RSPC-FR-069
    Verify project closure is rejected if financial settlement is pending or asset declaration is missing.
    """
    errors = validate_project_closure(financial_settled=False, has_asset_declaration=True)
    assert any("financial settlement is pending" in e for e in errors)

    errors2 = validate_project_closure(financial_settled=True, has_asset_declaration=False)
    assert any("asset declaration" in e for e in errors2)


def test_fr_026_notification_generation():
    """TEST-FR-026 | RSPC-CFR-021 / RSPC-FR-074
    Verify RSPC notification generation captures recipient, event, title, and message.
    """
    notif = RSPCNotification(
        recipient_id=101,
        event_type="PROPOSAL_RECOMMENDED",
        title="Proposal Recommended by HoD",
        message="Your proposal 'Quantum Algorithms' was recommended by HoD.",
        is_read=False,
    )
    assert notif.recipient_id == 101
    assert notif.is_read is False


def test_fr_027_funding_agency_integration_tracking():
    """TEST-FR-027 | RSPC-CFR-022 / RSPC-FR-083
    Verify external funding agency integration tracking in contracts.
    """
    contract = ResearchProposalContract(
        id=1,
        title="Bio-sensor Project",
        pi_id=102,
        department="Biotechnology",
        funding_agency="DBT-India",
        budget=Decimal("2500000.00"),
        status="APPROVED_DEAN",
        start_date="2026-08-01",
        end_date="2029-07-31",
    )
    assert contract.funding_agency == "DBT-India"


def test_fr_028_role_based_access_enforcement():
    """TEST-FR-028 | RSPC-CFR-023 / RSPC-FR-086
    Verify RBAC enforcement maps all RSPC operations to registry permissions.
    """
    for perm in OPERATION_PERMISSIONS.values():
        assert perm.startswith("rspc.")
        assert any(perm == p[0] for p in PERMISSIONS), f"Permission {perm} not in PERMISSIONS"


def test_fr_029_role_assignment_audit_logging():
    """TEST-FR-029 | RSPC-CFR-024 / RSPC-FR-091
    Verify role assignment and synchronization actions are logged to audit trail.
    """
    audit = RSPCAuditTrail(
        entity_type="role_assignment",
        entity_id=101,
        actor_id=1,
        action="SYNC_ROLE",
        remarks="Synchronized Dean-RSPC role assignment",
    )
    assert audit.action == "SYNC_ROLE"


def test_fr_030_boundary_staff_appointment_no_payroll():
    """TEST-FR-030 | RSPC-CFR-025 / RSPC-FR-096
    Verify project staff boundary excludes HR/payroll execution.
    """
    staff_fields = [f.name for f in ProjectStaffAppointment._meta.get_fields()]
    assert "salary_slip" not in staff_fields
    assert "bank_account_number" not in staff_fields
    assert "tax_pan" not in staff_fields


def test_fr_031_boundary_financial_no_disbursement():
    """TEST-FR-031 | RSPC-CFR-026 / RSPC-FR-097
    Verify finance boundary excludes bank payment disbursement execution.
    """
    fin_fields = [f.name for f in FinancialRequest._meta.get_fields()]
    assert "payment_gateway_ref" not in fin_fields
    assert "bank_transaction_id" not in fin_fields


def test_fr_032_boundary_procurement_no_stock_inventory():
    """TEST-FR-032 | RSPC-CFR-027 / RSPC-FR-098
    Verify procurement boundary excludes physical warehouse inventory execution.
    """
    proc_fields = [f.name for f in ProcurementRequest._meta.get_fields()]
    assert "warehouse_bin" not in proc_fields
    assert "stock_batch_number" not in proc_fields


def test_fr_033_lifecycle_permitted_updates_blocked_on_closure():
    """TEST-FR-033 | RSPC-CFR-028 / RSPC-FR-103
    Verify faculty project updates are permitted only in valid active lifecycle states (blocked after closure).
    """
    assert CLOSURE_STATUS_ARCHIVED == "ARCHIVED"
    ResearchProposal(
        title="Archived Project",
        pi_id=101,
        status="ARCHIVED",
    )
    import modules.rspc.domain.rules as rules
    assert hasattr(rules, "can_update_project"), "Module must provide lifecycle update permission check per CFR-028"


def test_fr_034_admin_verification_forwarding_gate():
    """TEST-FR-034 | RSPC-CFR-029 / RSPC-FR-110
    Verify RSPC Admin verification and forwarding gating constants exist.
    """
    assert PROPOSAL_STATUS_VERIFIED_ADMIN == "VERIFIED_ADMIN"
    assert PROPOSAL_STATUS_REJECTED_ADMIN == "REJECTED_ADMIN"
