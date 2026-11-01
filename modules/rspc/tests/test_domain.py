"""Fast pure-Python domain tests for RSPC state machines, workflows, and business rules.
Requires no database or network.
"""

from decimal import Decimal

import pytest

from modules.rspc.domain import (
    CLOSURE_TRANSITIONS,
    CONSULTANCY_TRANSITIONS,
    DEFAULT_DEAN_FINANCIAL_LIMIT,
    DEFAULT_DIRECTOR_FUNDING_THRESHOLD,
    FINANCE_TRANSITIONS,
    PROCUREMENT_TRANSITIONS,
    PROPOSAL_TRANSITIONS,
    STAFF_TRANSITIONS,
    BudgetExceededError,
    ClosureStatus,
    ConsultancyStatus,
    FinancialRequestStatus,
    GuardFailedError,
    InvalidTransitionError,
    MandatoryFieldMissingError,
    PermissionDeniedDomainError,
    ProcurementStatus,
    ProposalStatus,
    RspcRole,
    StaffAppointmentStatus,
    validate_transition,
)


# ===========================================================================
# 1. Proposal State Machine & Workflows (CW-RSPC-01, BW-RSPC-01, BW-RSPC-02)
# ===========================================================================
def test_bw_rspc_01_proposal_approved_at_dean():
    """BW-RSPC-01: Proposal Draft -> Submitted -> Dept Recommended -> Admin Verified -> Approved."""
    # Step 1: Draft -> Submitted (Faculty, BR-RSPC-013, 014)
    t1 = validate_transition(
        transitions=PROPOSAL_TRANSITIONS,
        from_state=ProposalStatus.DRAFT.value,
        to_state=ProposalStatus.SUBMITTED.value,
        actor_role=RspcRole.FACULTY.value,
        context={"required_fields": ["title", "budget"], "title": "AI Research", "budget": 50000},
    )
    assert t1.to == ProposalStatus.SUBMITTED.value

    # Step 2: Submitted -> Department Recommended (HoD, BR-RSPC-012, 067, 015, 016)
    t2 = validate_transition(
        transitions=PROPOSAL_TRANSITIONS,
        from_state=ProposalStatus.SUBMITTED.value,
        to_state=ProposalStatus.DEPT_RECOMMENDED.value,
        actor_role=RspcRole.HOD.value,
        context={"remarks": "Department strongly recommends this project."},
    )
    assert t2.to == ProposalStatus.DEPT_RECOMMENDED.value

    # Step 3: Dept Recommended -> Admin Verified (RSPC Admin, BR-RSPC-066, 070, 015, 016)
    t3 = validate_transition(
        transitions=PROPOSAL_TRANSITIONS,
        from_state=ProposalStatus.DEPT_RECOMMENDED.value,
        to_state=ProposalStatus.ADMIN_VERIFIED.value,
        actor_role=RspcRole.RSPC_ADMIN.value,
        context={"is_eligible": True},
    )
    assert t3.to == ProposalStatus.ADMIN_VERIFIED.value

    # Step 4: Admin Verified -> Approved (Dean-RSPC, BR-RSPC-068, 015, 016)
    t4 = validate_transition(
        transitions=PROPOSAL_TRANSITIONS,
        from_state=ProposalStatus.ADMIN_VERIFIED.value,
        to_state=ProposalStatus.APPROVED.value,
        actor_role=RspcRole.DEAN_RSPC.value,
        context={"budget_amount": Decimal("1000000"), "remarks": "Approved within Dean powers."},
    )
    assert t4.to == ProposalStatus.APPROVED.value


def test_bw_rspc_02_proposal_approved_via_director():
    """BW-RSPC-02: Proposal requiring Director action due to high value."""
    # Step 1: Admin Verified -> Forwarded to Director (BR-RSPC-004, 068, 069)
    t_fwd = validate_transition(
        transitions=PROPOSAL_TRANSITIONS,
        from_state=ProposalStatus.ADMIN_VERIFIED.value,
        to_state=ProposalStatus.FORWARDED_TO_DIRECTOR.value,
        actor_role=RspcRole.DEAN_RSPC.value,
        context={
            "budget_amount": DEFAULT_DIRECTOR_FUNDING_THRESHOLD + Decimal("100000"),
            "remarks": "Exceeds 50L limit; forwarding to Director.",
        },
    )
    assert t_fwd.to == ProposalStatus.FORWARDED_TO_DIRECTOR.value

    # Step 2: Forwarded to Director -> Approved (Director, BR-RSPC-005, 069, 070)
    t_app = validate_transition(
        transitions=PROPOSAL_TRANSITIONS,
        from_state=ProposalStatus.FORWARDED_TO_DIRECTOR.value,
        to_state=ProposalStatus.APPROVED.value,
        actor_role=RspcRole.DIRECTOR.value,
        context={"remarks": "Director authorization granted."},
    )
    assert t_app.to == ProposalStatus.APPROVED.value


def test_proposal_rejection_outcomes():
    """CW-RSPC-01: Rejection and non-recommendation outcomes."""
    # HoD not recommended (BR-RSPC-067)
    t_hod_rej = validate_transition(
        transitions=PROPOSAL_TRANSITIONS,
        from_state=ProposalStatus.SUBMITTED.value,
        to_state=ProposalStatus.DEPT_NOT_RECOMMENDED.value,
        actor_role=RspcRole.HOD.value,
        context={"remarks": "Feasibility concerns."},
    )
    assert t_hod_rej.to == ProposalStatus.DEPT_NOT_RECOMMENDED.value

    # Admin marks not eligible (BR-RSPC-066)
    t_admin_rej = validate_transition(
        transitions=PROPOSAL_TRANSITIONS,
        from_state=ProposalStatus.DEPT_RECOMMENDED.value,
        to_state=ProposalStatus.NOT_ELIGIBLE.value,
        actor_role=RspcRole.RSPC_ADMIN.value,
        context={"remarks": "Missing mandatory agency certificates."},
    )
    assert t_admin_rej.to == ProposalStatus.NOT_ELIGIBLE.value

    # Dean rejects (BR-RSPC-068)
    t_dean_rej = validate_transition(
        transitions=PROPOSAL_TRANSITIONS,
        from_state=ProposalStatus.ADMIN_VERIFIED.value,
        to_state=ProposalStatus.DEAN_NOT_APPROVED.value,
        actor_role=RspcRole.DEAN_RSPC.value,
        context={"remarks": "Budget heads non-compliant."},
    )
    assert t_dean_rej.to == ProposalStatus.DEAN_NOT_APPROVED.value


def test_proposal_mandatory_fields_missing_fails():
    """BR-RSPC-013: Mandatory fields must not be empty on submission."""
    with pytest.raises(MandatoryFieldMissingError):
        validate_transition(
            transitions=PROPOSAL_TRANSITIONS,
            from_state=ProposalStatus.DRAFT.value,
            to_state=ProposalStatus.SUBMITTED.value,
            actor_role=RspcRole.FACULTY.value,
            context={"required_fields": ["title", "budget"], "title": ""},
        )


def test_proposal_remarks_mandatory_on_review():
    """BR-RSPC-016: Decision remarks are mandatory."""
    with pytest.raises(GuardFailedError, match="Remarks are required"):
        validate_transition(
            transitions=PROPOSAL_TRANSITIONS,
            from_state=ProposalStatus.SUBMITTED.value,
            to_state=ProposalStatus.DEPT_RECOMMENDED.value,
            actor_role=RspcRole.HOD.value,
            context={"remarks": ""},
        )


# ===========================================================================
# 2. Consultancy Workflows (CW-RSPC-02, BW-RSPC-03, BW-RSPC-04)
# ===========================================================================
def test_bw_rspc_03_consultancy_approved_at_dean():
    """BW-RSPC-03: Consultancy approved at Dean-RSPC."""
    t1 = validate_transition(
        transitions=CONSULTANCY_TRANSITIONS,
        from_state=ConsultancyStatus.DRAFT.value,
        to_state=ConsultancyStatus.SUBMITTED.value,
        actor_role=RspcRole.FACULTY.value,
    )
    assert t1.to == ConsultancyStatus.SUBMITTED.value

    t2 = validate_transition(
        transitions=CONSULTANCY_TRANSITIONS,
        from_state=ConsultancyStatus.SUBMITTED.value,
        to_state=ConsultancyStatus.DEPT_RECOMMENDED.value,
        actor_role=RspcRole.HOD.value,
        context={"remarks": "Aligned with departmental expertise."},
    )
    assert t2.to == ConsultancyStatus.DEPT_RECOMMENDED.value

    t3 = validate_transition(
        transitions=CONSULTANCY_TRANSITIONS,
        from_state=ConsultancyStatus.DEPT_RECOMMENDED.value,
        to_state=ConsultancyStatus.ADMIN_VERIFIED.value,
        actor_role=RspcRole.RSPC_ADMIN.value,
    )
    assert t3.to == ConsultancyStatus.ADMIN_VERIFIED.value

    t4 = validate_transition(
        transitions=CONSULTANCY_TRANSITIONS,
        from_state=ConsultancyStatus.ADMIN_VERIFIED.value,
        to_state=ConsultancyStatus.APPROVED.value,
        actor_role=RspcRole.DEAN_RSPC.value,
        context={"budget_amount": Decimal("500000"), "remarks": "Approved."},
    )
    assert t4.to == ConsultancyStatus.APPROVED.value


def test_bw_rspc_04_consultancy_approved_via_director():
    """BW-RSPC-04: Consultancy forwarded to and approved by Director."""
    t_fwd = validate_transition(
        transitions=CONSULTANCY_TRANSITIONS,
        from_state=ConsultancyStatus.ADMIN_VERIFIED.value,
        to_state=ConsultancyStatus.FORWARDED_TO_DIRECTOR.value,
        actor_role=RspcRole.DEAN_RSPC.value,
        context={"budget_amount": Decimal("6000000"), "remarks": "High-value consultancy."},
    )
    assert t_fwd.to == ConsultancyStatus.FORWARDED_TO_DIRECTOR.value

    t_dir = validate_transition(
        transitions=CONSULTANCY_TRANSITIONS,
        from_state=ConsultancyStatus.FORWARDED_TO_DIRECTOR.value,
        to_state=ConsultancyStatus.APPROVED.value,
        actor_role=RspcRole.DIRECTOR.value,
        context={"remarks": "Director approved."},
    )
    assert t_dir.to == ConsultancyStatus.APPROVED.value


# ===========================================================================
# 3. Staff Appointment Workflows (CW-RSPC-03, BW-RSPC-05, BW-RSPC-06)
# ===========================================================================
def test_bw_rspc_05_staff_appointment_dean_approval():
    """BW-RSPC-05: Staff Appointment approved at Dean-RSPC."""
    t1 = validate_transition(
        transitions=STAFF_TRANSITIONS,
        from_state=StaffAppointmentStatus.DRAFT.value,
        to_state=StaffAppointmentStatus.REQUESTED.value,
        actor_role=RspcRole.FACULTY.value,
    )
    assert t1.to == StaffAppointmentStatus.REQUESTED.value

    t2 = validate_transition(
        transitions=STAFF_TRANSITIONS,
        from_state=StaffAppointmentStatus.REQUESTED.value,
        to_state=StaffAppointmentStatus.ADMIN_VERIFIED.value,
        actor_role=RspcRole.RSPC_ADMIN.value,
    )
    assert t2.to == StaffAppointmentStatus.ADMIN_VERIFIED.value

    # Selection recommendation by Faculty (UC-022)
    t3 = validate_transition(
        transitions=STAFF_TRANSITIONS,
        from_state=StaffAppointmentStatus.ADMIN_VERIFIED.value,
        to_state=StaffAppointmentStatus.SELECTION_RECOMMENDED.value,
        actor_role=RspcRole.FACULTY.value,
        context={"recommendation": "Candidate selected based on interview merit."},
    )
    assert t3.to == StaffAppointmentStatus.SELECTION_RECOMMENDED.value

    t4 = validate_transition(
        transitions=STAFF_TRANSITIONS,
        from_state=StaffAppointmentStatus.SELECTION_RECOMMENDED.value,
        to_state=StaffAppointmentStatus.APPROVED.value,
        actor_role=RspcRole.DEAN_RSPC.value,
        context={"remarks": "Staff appointment approved."},
    )
    assert t4.to == StaffAppointmentStatus.APPROVED.value


# ===========================================================================
# 4. Financial & Fund Requests (CW-RSPC-04, BW-RSPC-07, BW-RSPC-08)
# ===========================================================================
def test_bw_rspc_07_financial_approved_at_dean():
    """BW-RSPC-07: Financial Request approved within Dean powers."""
    t1 = validate_transition(
        transitions=FINANCE_TRANSITIONS,
        from_state=FinancialRequestStatus.DRAFT.value,
        to_state=FinancialRequestStatus.SUBMITTED.value,
        actor_role=RspcRole.FACULTY.value,
        context={"amount": 100000, "available_budget": 500000},
    )
    assert t1.to == FinancialRequestStatus.SUBMITTED.value

    t2 = validate_transition(
        transitions=FINANCE_TRANSITIONS,
        from_state=FinancialRequestStatus.SUBMITTED.value,
        to_state=FinancialRequestStatus.VERIFIED.value,
        actor_role=RspcRole.RSPC_ADMIN.value,
    )
    assert t2.to == FinancialRequestStatus.VERIFIED.value

    t3 = validate_transition(
        transitions=FINANCE_TRANSITIONS,
        from_state=FinancialRequestStatus.VERIFIED.value,
        to_state=FinancialRequestStatus.APPROVED.value,
        actor_role=RspcRole.DEAN_RSPC.value,
        context={"amount": Decimal("100000"), "remarks": "Approved within 5L limit."},
    )
    assert t3.to == FinancialRequestStatus.APPROVED.value


def test_financial_request_budget_exceeded_fails():
    """BR-RSPC-035/059: Financial request exceeding budget fails."""
    with pytest.raises(BudgetExceededError):
        validate_transition(
            transitions=FINANCE_TRANSITIONS,
            from_state=FinancialRequestStatus.DRAFT.value,
            to_state=FinancialRequestStatus.SUBMITTED.value,
            actor_role=RspcRole.FACULTY.value,
            context={"amount": 600000, "available_budget": 200000},
        )


def test_financial_request_escalation_to_director():
    """BR-RSPC-033, BW-RSPC-08: High-value financial request forwarded to Director."""
    t_fwd = validate_transition(
        transitions=FINANCE_TRANSITIONS,
        from_state=FinancialRequestStatus.VERIFIED.value,
        to_state=FinancialRequestStatus.FORWARDED_TO_DIRECTOR.value,
        actor_role=RspcRole.DEAN_RSPC.value,
        context={
            "amount": DEFAULT_DEAN_FINANCIAL_LIMIT + Decimal("50000"),
            "remarks": "Amount exceeds Dean delegated limit.",
        },
    )
    assert t_fwd.to == FinancialRequestStatus.FORWARDED_TO_DIRECTOR.value

    t_dir = validate_transition(
        transitions=FINANCE_TRANSITIONS,
        from_state=FinancialRequestStatus.FORWARDED_TO_DIRECTOR.value,
        to_state=FinancialRequestStatus.APPROVED.value,
        actor_role=RspcRole.DIRECTOR.value,
        context={"remarks": "Director approved expenditure."},
    )
    assert t_dir.to == FinancialRequestStatus.APPROVED.value


# ===========================================================================
# 5. Procurement Workflows (CW-RSPC-05, BW-RSPC-09, BW-RSPC-10)
# ===========================================================================
def test_bw_rspc_09_procurement_approved_at_dean():
    """BW-RSPC-09: Procurement approved at Dean-RSPC."""
    t1 = validate_transition(
        transitions=PROCUREMENT_TRANSITIONS,
        from_state=ProcurementStatus.DRAFT.value,
        to_state=ProcurementStatus.SUBMITTED.value,
        actor_role=RspcRole.FACULTY.value,
        context={"amount": 200000, "available_budget": 500000},
    )
    assert t1.to == ProcurementStatus.SUBMITTED.value

    t2 = validate_transition(
        transitions=PROCUREMENT_TRANSITIONS,
        from_state=ProcurementStatus.SUBMITTED.value,
        to_state=ProcurementStatus.VERIFIED.value,
        actor_role=RspcRole.RSPC_ADMIN.value,
        context={"amount": 200000, "available_budget": 500000},
    )
    assert t2.to == ProcurementStatus.VERIFIED.value

    t3 = validate_transition(
        transitions=PROCUREMENT_TRANSITIONS,
        from_state=ProcurementStatus.VERIFIED.value,
        to_state=ProcurementStatus.APPROVED.value,
        actor_role=RspcRole.DEAN_RSPC.value,
        context={"estimated_cost": Decimal("200000"), "remarks": "Procurement approved."},
    )
    assert t3.to == ProcurementStatus.APPROVED.value


# ===========================================================================
# 6. Project Closure Workflows (CW-RSPC-06, BW-RSPC-11, BW-RSPC-12)
# ===========================================================================
def test_bw_rspc_11_project_closure_and_archival():
    """BW-RSPC-11: Project Closure approved and archived at Dean-RSPC (BR-RSPC-043)."""
    t1 = validate_transition(
        transitions=CLOSURE_TRANSITIONS,
        from_state=ClosureStatus.DRAFT.value,
        to_state=ClosureStatus.SUBMITTED.value,
        actor_role=RspcRole.FACULTY.value,
        context={"completion_report": "Project objectives achieved successfully."},
    )
    assert t1.to == ClosureStatus.SUBMITTED.value

    t2 = validate_transition(
        transitions=CLOSURE_TRANSITIONS,
        from_state=ClosureStatus.SUBMITTED.value,
        to_state=ClosureStatus.VERIFIED.value,
        actor_role=RspcRole.RSPC_ADMIN.value,
        context={"settlement_verified": True, "assets_verified": True},
    )
    assert t2.to == ClosureStatus.VERIFIED.value

    t3 = validate_transition(
        transitions=CLOSURE_TRANSITIONS,
        from_state=ClosureStatus.VERIFIED.value,
        to_state=ClosureStatus.ARCHIVED.value,
        actor_role=RspcRole.DEAN_RSPC.value,
        context={"budget_amount": Decimal("1000000"), "remarks": "Project closed and archived."},
    )
    assert t3.to == ClosureStatus.ARCHIVED.value


def test_unauthorized_role_transition_refused():
    """BR-RSPC-049: Actions are restricted by assigned role."""
    with pytest.raises(PermissionDeniedDomainError):
        validate_transition(
            transitions=PROPOSAL_TRANSITIONS,
            from_state=ProposalStatus.ADMIN_VERIFIED.value,
            to_state=ProposalStatus.APPROVED.value,
            actor_role=RspcRole.FACULTY.value,  # Faculty cannot approve proposals
            context={"remarks": "Self-approval attempt"},
        )


def test_illegal_state_transition_refused():
    """State machine prevents illegal backwards or skipping transitions."""
    with pytest.raises(InvalidTransitionError):
        validate_transition(
            transitions=PROPOSAL_TRANSITIONS,
            from_state=ProposalStatus.DRAFT.value,
            to_state=ProposalStatus.APPROVED.value,  # Cannot jump from draft to approved
            actor_role=RspcRole.DEAN_RSPC.value,
        )
