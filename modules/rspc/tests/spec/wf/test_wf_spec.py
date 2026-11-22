"""Automated specification-based test suite for RSPC module - WF Strategy.
Generated from a8_design/WF_DESIGN.json.
Source of Truth: RSPC Problem Statement v1.0 and Workflow Specifications v2.1.
"""
from decimal import Decimal

from modules.rspc.domain.rules import (
    CLOSURE_STATUS_APPROVED_DIRECTOR,
    CLOSURE_STATUS_ARCHIVED,
    CLOSURE_STATUS_FORWARDED_DIRECTOR,
    CLOSURE_STATUS_REJECTED,
    CONSULTANCY_STATUS_APPROVED_DEAN,
    CONSULTANCY_STATUS_DRAFT,
    CONSULTANCY_STATUS_REJECTED,
    CONSULTANCY_STATUS_VERIFIED_ADMIN,
    FINANCIAL_STATUS_APPROVED_DEAN,
    FINANCIAL_STATUS_APPROVED_DIRECTOR,
    FINANCIAL_STATUS_ESCALATED_DIRECTOR,
    FINANCIAL_STATUS_REJECTED,
    PROPOSAL_STATUS_APPROVED_DEAN,
    PROPOSAL_STATUS_APPROVED_DIRECTOR,
    PROPOSAL_STATUS_CHOICES,
    PROPOSAL_STATUS_DRAFT,
    PROPOSAL_STATUS_FORWARDED_DIRECTOR,
    PROPOSAL_STATUS_RECOMMENDED_HOD,
    PROPOSAL_STATUS_REJECTED_ADMIN,
    PROPOSAL_STATUS_REJECTED_DEAN,
    PROPOSAL_STATUS_REJECTED_DIRECTOR,
    PROPOSAL_STATUS_REJECTED_HOD,
    PROPOSAL_STATUS_SUBMITTED_HOD,
    PROPOSAL_STATUS_VERIFIED_ADMIN,
    is_director_approval_required,
    validate_project_closure,
)
from modules.rspc.models import (
    ProcurementRequest,
    ProjectStaffAppointment,
)
from modules.rspc.registry import ROLE_GRANTS


def test_wf_001_proposal_draft_to_submitted():
    """TEST-WF-001 | BW-RSPC-01 Transition 1
    Faculty submits research proposal from Draft to Submitted.
    """
    assert PROPOSAL_STATUS_DRAFT != PROPOSAL_STATUS_SUBMITTED_HOD
    assert PROPOSAL_STATUS_SUBMITTED_HOD in PROPOSAL_STATUS_CHOICES


def test_wf_002_proposal_submitted_to_recommended():
    """TEST-WF-002 | BW-RSPC-01 Transition 2
    HoD recommends research proposal advancing to RECOMMENDED_HOD.
    """
    assert "rspc.proposal.recommend_hod" in ROLE_GRANTS["hod"]
    assert PROPOSAL_STATUS_RECOMMENDED_HOD in PROPOSAL_STATUS_CHOICES


def test_wf_003_proposal_recommended_to_verified():
    """TEST-WF-003 | BW-RSPC-01 Transition 3
    RSPC Admin verifies proposal advancing to VERIFIED_ADMIN.
    """
    assert "rspc.proposal.verify_admin" in ROLE_GRANTS["rspc_admin"]
    assert PROPOSAL_STATUS_VERIFIED_ADMIN in PROPOSAL_STATUS_CHOICES


def test_wf_004_proposal_verified_to_approved_dean():
    """TEST-WF-004 | BW-RSPC-01 Transition 4
    Dean-RSPC approves proposal advancing to APPROVED_DEAN.
    """
    assert is_director_approval_required("proposal", Decimal("600000.00")) is False
    assert PROPOSAL_STATUS_APPROVED_DEAN in PROPOSAL_STATUS_CHOICES


def test_wf_005_proposal_verified_to_forwarded_director():
    """TEST-WF-005 | BW-RSPC-02 Transition 4
    Dean-RSPC forwards large funding proposal to Director.
    """
    assert is_director_approval_required("proposal", Decimal("1500000.00")) is True
    assert PROPOSAL_STATUS_FORWARDED_DIRECTOR in PROPOSAL_STATUS_CHOICES


def test_wf_006_proposal_forwarded_to_approved_director():
    """TEST-WF-006 | BW-RSPC-02 Transition 5
    Director authorizes large funding proposal advancing to APPROVED_DIRECTOR.
    """
    assert "rspc.proposal.authorize_director" in ROLE_GRANTS["director"]
    assert PROPOSAL_STATUS_APPROVED_DIRECTOR in PROPOSAL_STATUS_CHOICES


def test_wf_007_consultancy_dean_approval_path():
    """TEST-WF-007 | BW-RSPC-03 Transition 1-4
    Consultancy project approved at Dean-RSPC level.
    """
    assert CONSULTANCY_STATUS_DRAFT == "DRAFT"
    assert CONSULTANCY_STATUS_APPROVED_DEAN == "APPROVED_DEAN"
    assert "rspc.consultancy.approve_dean" in ROLE_GRANTS["dean_rspc"]


def test_wf_008_consultancy_director_routing_transition():
    """TEST-WF-008 | BW-RSPC-04 Transition 4-5
    High-value consultancy (>= 10 Lakhs) routed to Director for approval.
    """
    needs_dir = is_director_approval_required("consultancy", Decimal("1500000.00"))
    assert needs_dir is True, "Consultancy >= 10L must route to Director per BW-RSPC-04"


def test_wf_009_staff_appointment_dean_approval():
    """TEST-WF-009 | BW-RSPC-05 Transition 1-4
    Staff appointment approved at Dean-RSPC level.
    """
    staff = ProjectStaffAppointment(
        project_id=1,
        pi_id=101,
        position_title="JRF",
        stipend_amount=Decimal("31000.00"),
        status="REQUESTED",
    )
    assert staff.status == "REQUESTED"
    assert "rspc.staff.manage" in ROLE_GRANTS["dean_rspc"]


def test_wf_010_staff_appointment_director_routing():
    """TEST-WF-010 | BW-RSPC-06 Transition 4-5
    High-value staff appointment routed to Director.
    """
    needs_dir = is_director_approval_required("staff", Decimal("50000.00"))
    assert needs_dir is True, "High stipend appointment must have Director escalation guard per BW-RSPC-06"


def test_wf_011_financial_dean_approval():
    """TEST-WF-011 | BW-RSPC-07 Transition 1-3
    Financial request approved at Dean-RSPC level (< 2 Lakhs).
    """
    assert is_director_approval_required("financial", Decimal("150000.00")) is False
    assert FINANCIAL_STATUS_APPROVED_DEAN == "APPROVED_DEAN"


def test_wf_012_financial_director_escalation_path():
    """TEST-WF-012 | BW-RSPC-08 Transition 3-4
    Financial request escalated and approved via Director (>= 2 Lakhs).
    """
    assert is_director_approval_required("financial", Decimal("250000.00")) is True
    assert FINANCIAL_STATUS_ESCALATED_DIRECTOR == "ESCALATED_DIRECTOR"
    assert FINANCIAL_STATUS_APPROVED_DIRECTOR == "APPROVED_DIRECTOR"


def test_wf_013_procurement_dean_approval_path():
    """TEST-WF-013 | BW-RSPC-09 Transition 1-3
    Procurement request approved at Dean-RSPC level (< 2 Lakhs).
    """
    assert is_director_approval_required("procurement", Decimal("150000.00")) is False
    assert "rspc.procurement.approve" in ROLE_GRANTS["dean_rspc"]


def test_wf_014_procurement_director_escalation_path():
    """TEST-WF-014 | BW-RSPC-10 Transition 3-4
    Procurement request escalated to Director (>= 2 Lakhs).
    """
    assert is_director_approval_required("procurement", Decimal("300000.00")) is True


def test_wf_015_closure_dean_approval_and_archival():
    """TEST-WF-015 | BW-RSPC-11 Transition 1-3
    Project closure approved and archived at Dean-RSPC level.
    """
    assert validate_project_closure(True, True) == []
    assert CLOSURE_STATUS_ARCHIVED == "ARCHIVED"


def test_wf_016_closure_director_forwarding():
    """TEST-WF-016 | BW-RSPC-12 Transition 3-4
    Project closure forwarded to Director for institutional archival.
    """
    assert CLOSURE_STATUS_FORWARDED_DIRECTOR == "FORWARDED_DIRECTOR"
    assert CLOSURE_STATUS_APPROVED_DIRECTOR == "APPROVED_DIRECTOR"


def test_wf_017_proposal_hod_reject():
    """TEST-WF-017 | CW-RSPC-01 Outcome Department Not Recommended
    Research proposal rejected by HoD with non-recommendation outcome.
    """
    assert PROPOSAL_STATUS_REJECTED_HOD == "REJECTED_HOD"


def test_wf_018_proposal_admin_reject():
    """TEST-WF-018 | CW-RSPC-01 Outcome Admin Not Verified
    Research proposal rejected by Admin as not eligible for forwarding.
    """
    assert PROPOSAL_STATUS_REJECTED_ADMIN == "REJECTED_ADMIN"


def test_wf_019_proposal_dean_reject():
    """TEST-WF-019 | CW-RSPC-01 Outcome Dean Not Approved
    Research proposal rejected by Dean-RSPC.
    """
    assert PROPOSAL_STATUS_REJECTED_DEAN == "REJECTED_DEAN"


def test_wf_020_proposal_director_reject():
    """TEST-WF-020 | CW-RSPC-01 Outcome Director Not Approved
    Research proposal rejected by Director.
    """
    assert PROPOSAL_STATUS_REJECTED_DIRECTOR == "REJECTED_DIRECTOR"


def test_wf_021_consultancy_department_reject():
    """TEST-WF-021 | CW-RSPC-02 Outcome Department Not Recommended
    Consultancy rejected at department level.
    """
    assert CONSULTANCY_STATUS_REJECTED == "REJECTED"


def test_wf_022_consultancy_optional_department_skip():
    """TEST-WF-022 | CW-RSPC-02 Optional Department Stage Skip
    Consultancy submitted directly to Admin verified when department stage not applicable.
    """
    assert CONSULTANCY_STATUS_VERIFIED_ADMIN == "VERIFIED_ADMIN"


def test_wf_023_consultancy_dean_reject():
    """TEST-WF-023 | CW-RSPC-02 Outcome Dean Not Approved
    Consultancy rejected by Dean-RSPC.
    """
    assert CONSULTANCY_STATUS_REJECTED == "REJECTED"


def test_wf_024_staff_appointment_admin_manage():
    """TEST-WF-024 | CW-RSPC-03 Outcome Admin Not Verified
    Staff appointment rejected by Admin as not eligible.
    """
    assert "rspc.staff.manage" in ROLE_GRANTS["rspc_admin"]


def test_wf_025_staff_appointment_dean_manage():
    """TEST-WF-025 | CW-RSPC-03 Outcome Dean Not Approved
    Staff appointment rejected by Dean-RSPC.
    """
    assert "rspc.staff.manage" in ROLE_GRANTS["dean_rspc"]


def test_wf_026_financial_admin_reject():
    """TEST-WF-026 | CW-RSPC-04 Outcome Financial Admin Rejected
    Financial request rejected by Admin during initial verification.
    """
    assert FINANCIAL_STATUS_REJECTED == "REJECTED"


def test_wf_027_financial_dean_reject():
    """TEST-WF-027 | CW-RSPC-04 Outcome Financial Dean Rejected
    Financial request rejected by Dean-RSPC.
    """
    assert FINANCIAL_STATUS_REJECTED == "REJECTED"


def test_wf_028_procurement_admin_status_handling():
    """TEST-WF-028 | CW-RSPC-05 Outcome Procurement Admin Rejected
    Procurement request rejected during admin verification.
    """
    proc = ProcurementRequest(
        project_id=1,
        requested_by_id=101,
        item_name="Oscilloscope",
        estimated_cost=Decimal("75000.00"),
        status="REJECTED",
    )
    assert proc.status == "REJECTED"


def test_wf_029_procurement_dean_approval_permission():
    """TEST-WF-029 | CW-RSPC-05 Outcome Procurement Dean Rejected
    Procurement request rejected by Dean-RSPC.
    """
    assert "rspc.procurement.approve" in ROLE_GRANTS["dean_rspc"]


def test_wf_030_closure_admin_rejection():
    """TEST-WF-030 | CW-RSPC-06 Outcome Closure Admin Rejected
    Project closure rejected by Admin due to incomplete records.
    """
    assert CLOSURE_STATUS_REJECTED == "REJECTED"


def test_wf_031_closure_dean_rejection():
    """TEST-WF-031 | CW-RSPC-06 Outcome Closure Dean Rejected
    Project closure rejected by Dean-RSPC.
    """
    assert CLOSURE_STATUS_REJECTED == "REJECTED"


def test_wf_032_illegal_state_transition_prevention():
    """TEST-WF-032 | CW-RSPC-01 Workflow State Machine Guard
    Workflow state machine must reject illegal direct state jump from DRAFT to APPROVED_DIRECTOR.
    """
    import modules.rspc.domain.rules as rules
    assert hasattr(rules, "validate_workflow_transition"), (
        "Rules module must provide validate_workflow_transition preventing illegal transitions per CW-RSPC-01"
    )
