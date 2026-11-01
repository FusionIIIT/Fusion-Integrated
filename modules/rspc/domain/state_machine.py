"""RSPC State Machines and Transition Logic.
Pure Python — no Django, DRF, or Celery imports.
Encodes the state transitions from CW-RSPC-01 through CW-RSPC-06 and BW-RSPC-01 through BW-RSPC-12.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .entities import (
    DEFAULT_DEAN_FINANCIAL_LIMIT,
    DEFAULT_DEAN_PROCUREMENT_LIMIT,
    DEFAULT_DIRECTOR_FUNDING_THRESHOLD,
    ClosureStatus,
    ConsultancyStatus,
    FinancialRequestStatus,
    ProcurementStatus,
    ProposalStatus,
    RspcRole,
    StaffAppointmentStatus,
    WorkflowTransition,
)
from .errors import (
    BudgetExceededError,
    GuardFailedError,
    InvalidTransitionError,
    MandatoryFieldMissingError,
    PermissionDeniedDomainError,
)

# ---------------------------------------------------------------------------
# 1. Proposal State Machine (CW-RSPC-01, BW-RSPC-01, BW-RSPC-02)
# ---------------------------------------------------------------------------
PROPOSAL_TRANSITIONS: tuple[WorkflowTransition, ...] = (
    # S1: Draft -> Submitted (Faculty, RSPC-UC-002, BR-RSPC-013, BR-RSPC-014)
    WorkflowTransition(
        frm=ProposalStatus.DRAFT.value,
        to=ProposalStatus.SUBMITTED.value,
        actor_roles=frozenset({RspcRole.FACULTY.value}),
        permission="rspc.proposal.create",
        guards=("mandatory_fields_valid", "policy_validation_passed"),
        description="Faculty submits research proposal",
    ),
    # S2: Submitted -> Department Recommended (HoD, RSPC-UC-003, BR-RSPC-012, 067, 015, 016)
    WorkflowTransition(
        frm=ProposalStatus.SUBMITTED.value,
        to=ProposalStatus.DEPT_RECOMMENDED.value,
        actor_roles=frozenset({RspcRole.HOD.value}),
        permission="rspc.proposal.recommend_dept",
        guards=("has_remarks",),
        description="HoD recommends proposal",
    ),
    # S3: Submitted -> Department Not Recommended (HoD, RSPC-UC-003, BR-RSPC-012, 067, 015, 016)
    WorkflowTransition(
        frm=ProposalStatus.SUBMITTED.value,
        to=ProposalStatus.DEPT_NOT_RECOMMENDED.value,
        actor_roles=frozenset({RspcRole.HOD.value}),
        permission="rspc.proposal.recommend_dept",
        guards=("has_remarks",),
        description="HoD does not recommend proposal",
    ),
    # S4: Department Recommended -> Admin Verified
    # (RSPC Admin, RSPC-UC-004, BR-RSPC-066, 070, 015, 016)
    WorkflowTransition(
        frm=ProposalStatus.DEPT_RECOMMENDED.value,
        to=ProposalStatus.ADMIN_VERIFIED.value,
        actor_roles=frozenset({RspcRole.RSPC_ADMIN.value}),
        permission="rspc.proposal.verify",
        guards=("verification_eligible",),
        description="Admin verifies proposal completeness and compliance",
    ),
    # S5: Department Recommended -> Not Eligible (RSPC Admin, RSPC-UC-004, BR-RSPC-066, 070)
    WorkflowTransition(
        frm=ProposalStatus.DEPT_RECOMMENDED.value,
        to=ProposalStatus.NOT_ELIGIBLE.value,
        actor_roles=frozenset({RspcRole.RSPC_ADMIN.value}),
        permission="rspc.proposal.verify",
        guards=("has_remarks",),
        description="Admin marks proposal not eligible for forwarding",
    ),
    # S6: Admin Verified -> Approved (Dean-RSPC, RSPC-UC-005, BR-RSPC-068, 015, 016)
    WorkflowTransition(
        frm=ProposalStatus.ADMIN_VERIFIED.value,
        to=ProposalStatus.APPROVED.value,
        actor_roles=frozenset({RspcRole.DEAN_RSPC.value}),
        permission="rspc.proposal.approve_dean",
        guards=("within_dean_authority", "has_remarks"),
        description="Dean approves proposal directly",
    ),
    # S7: Admin Verified -> Forwarded to Director
    # (Dean-RSPC, RSPC-UC-005, BR-RSPC-004, 068, 069, 015, 016)
    WorkflowTransition(
        frm=ProposalStatus.ADMIN_VERIFIED.value,
        to=ProposalStatus.FORWARDED_TO_DIRECTOR.value,
        actor_roles=frozenset({RspcRole.DEAN_RSPC.value}),
        permission="rspc.proposal.approve_dean",
        guards=("requires_director_action", "has_remarks"),
        description="Dean forwards proposal to Director",
    ),
    # S8: Admin Verified -> Dean Not Approved (Dean-RSPC, RSPC-UC-005, BR-RSPC-068, 015, 016)
    WorkflowTransition(
        frm=ProposalStatus.ADMIN_VERIFIED.value,
        to=ProposalStatus.DEAN_NOT_APPROVED.value,
        actor_roles=frozenset({RspcRole.DEAN_RSPC.value}),
        permission="rspc.proposal.approve_dean",
        guards=("has_remarks",),
        description="Dean rejects proposal",
    ),
    # S9: Forwarded to Director -> Approved (Director, RSPC-UC-006, BR-RSPC-069, 070, 015, 016)
    WorkflowTransition(
        frm=ProposalStatus.FORWARDED_TO_DIRECTOR.value,
        to=ProposalStatus.APPROVED.value,
        actor_roles=frozenset({RspcRole.DIRECTOR.value}),
        permission="rspc.proposal.authorize_director",
        guards=("has_remarks",),
        description="Director approves proposal",
    ),
    # S10: Forwarded to Director -> Director Not Approved
    # (Director, RSPC-UC-006, BR-RSPC-069, 070, 015, 016)
    WorkflowTransition(
        frm=ProposalStatus.FORWARDED_TO_DIRECTOR.value,
        to=ProposalStatus.DIRECTOR_NOT_APPROVED.value,
        actor_roles=frozenset({RspcRole.DIRECTOR.value}),
        permission="rspc.proposal.authorize_director",
        guards=("has_remarks",),
        description="Director rejects proposal",
    ),
)


# ---------------------------------------------------------------------------
# 2. Consultancy State Machine (CW-RSPC-02, BW-RSPC-03, BW-RSPC-04)
# ---------------------------------------------------------------------------
CONSULTANCY_TRANSITIONS: tuple[WorkflowTransition, ...] = (
    # S1: Draft -> Submitted (Faculty, RSPC-UC-007, BR-RSPC-022)
    WorkflowTransition(
        frm=ConsultancyStatus.DRAFT.value,
        to=ConsultancyStatus.SUBMITTED.value,
        actor_roles=frozenset({RspcRole.FACULTY.value}),
        permission="rspc.consultancy.create",
        guards=("mandatory_fields_valid",),
        description="Faculty registers consultancy",
    ),
    # S2: Submitted -> Department Recommended (HoD, RSPC-UC-003, BR-RSPC-022, 067)
    WorkflowTransition(
        frm=ConsultancyStatus.SUBMITTED.value,
        to=ConsultancyStatus.DEPT_RECOMMENDED.value,
        actor_roles=frozenset({RspcRole.HOD.value}),
        permission="rspc.consultancy.recommend_dept",
        guards=("has_remarks",),
        description="HoD recommends consultancy",
    ),
    # S3: Submitted -> Department Not Recommended (HoD, RSPC-UC-003, BR-RSPC-022, 067)
    WorkflowTransition(
        frm=ConsultancyStatus.SUBMITTED.value,
        to=ConsultancyStatus.DEPT_NOT_RECOMMENDED.value,
        actor_roles=frozenset({RspcRole.HOD.value}),
        permission="rspc.consultancy.recommend_dept",
        guards=("has_remarks",),
        description="HoD does not recommend consultancy",
    ),
    # S4: Direct Submitted -> Admin Verified (Department stage omitted/optional, BR-RSPC-022)
    WorkflowTransition(
        frm=ConsultancyStatus.SUBMITTED.value,
        to=ConsultancyStatus.ADMIN_VERIFIED.value,
        actor_roles=frozenset({RspcRole.RSPC_ADMIN.value}),
        permission="rspc.consultancy.verify",
        guards=("verification_eligible",),
        description="Admin verifies consultancy directly if department review not required",
    ),
    # S5: Department Recommended -> Admin Verified (RSPC Admin, RSPC-UC-004, BR-RSPC-022, 066, 070)
    WorkflowTransition(
        frm=ConsultancyStatus.DEPT_RECOMMENDED.value,
        to=ConsultancyStatus.ADMIN_VERIFIED.value,
        actor_roles=frozenset({RspcRole.RSPC_ADMIN.value}),
        permission="rspc.consultancy.verify",
        guards=("verification_eligible",),
        description="Admin verifies consultancy after HoD recommendation",
    ),
    # S6: Submitted / Dept Recommended -> Not Eligible
    # (RSPC Admin, RSPC-UC-004, BR-RSPC-022, 066, 070)
    WorkflowTransition(
        frm=ConsultancyStatus.DEPT_RECOMMENDED.value,
        to=ConsultancyStatus.NOT_ELIGIBLE.value,
        actor_roles=frozenset({RspcRole.RSPC_ADMIN.value}),
        permission="rspc.consultancy.verify",
        guards=("has_remarks",),
        description="Admin rejects consultancy eligibility",
    ),
    WorkflowTransition(
        frm=ConsultancyStatus.SUBMITTED.value,
        to=ConsultancyStatus.NOT_ELIGIBLE.value,
        actor_roles=frozenset({RspcRole.RSPC_ADMIN.value}),
        permission="rspc.consultancy.verify",
        guards=("has_remarks",),
        description="Admin rejects consultancy eligibility directly",
    ),
    # S7: Admin Verified -> Approved (Dean-RSPC, RSPC-UC-005, BR-RSPC-022, 068)
    WorkflowTransition(
        frm=ConsultancyStatus.ADMIN_VERIFIED.value,
        to=ConsultancyStatus.APPROVED.value,
        actor_roles=frozenset({RspcRole.DEAN_RSPC.value}),
        permission="rspc.consultancy.approve_dean",
        guards=("within_dean_authority", "has_remarks"),
        description="Dean approves consultancy directly",
    ),
    # S8: Admin Verified -> Forwarded to Director (Dean-RSPC, RSPC-UC-005, BR-RSPC-004, 068, 069)
    WorkflowTransition(
        frm=ConsultancyStatus.ADMIN_VERIFIED.value,
        to=ConsultancyStatus.FORWARDED_TO_DIRECTOR.value,
        actor_roles=frozenset({RspcRole.DEAN_RSPC.value}),
        permission="rspc.consultancy.approve_dean",
        guards=("requires_director_action", "has_remarks"),
        description="Dean forwards consultancy to Director",
    ),
    # S9: Admin Verified -> Dean Not Approved (Dean-RSPC, RSPC-UC-005, BR-RSPC-068)
    WorkflowTransition(
        frm=ConsultancyStatus.ADMIN_VERIFIED.value,
        to=ConsultancyStatus.DEAN_NOT_APPROVED.value,
        actor_roles=frozenset({RspcRole.DEAN_RSPC.value}),
        permission="rspc.consultancy.approve_dean",
        guards=("has_remarks",),
        description="Dean rejects consultancy",
    ),
    # S10: Forwarded to Director -> Approved (Director, RSPC-UC-006, BR-RSPC-069, 070)
    WorkflowTransition(
        frm=ConsultancyStatus.FORWARDED_TO_DIRECTOR.value,
        to=ConsultancyStatus.APPROVED.value,
        actor_roles=frozenset({RspcRole.DIRECTOR.value}),
        permission="rspc.consultancy.authorize_director",
        guards=("has_remarks",),
        description="Director approves consultancy",
    ),
    # S11: Forwarded to Director -> Director Not Approved (Director, RSPC-UC-006, BR-RSPC-069, 070)
    WorkflowTransition(
        frm=ConsultancyStatus.FORWARDED_TO_DIRECTOR.value,
        to=ConsultancyStatus.DIRECTOR_NOT_APPROVED.value,
        actor_roles=frozenset({RspcRole.DIRECTOR.value}),
        permission="rspc.consultancy.authorize_director",
        guards=("has_remarks",),
        description="Director rejects consultancy",
    ),
)


# ---------------------------------------------------------------------------
# 3. Staff Appointment State Machine (CW-RSPC-03, BW-RSPC-05, BW-RSPC-06)
# ---------------------------------------------------------------------------
STAFF_TRANSITIONS: tuple[WorkflowTransition, ...] = (
    # S1: Draft -> Requested (Faculty, RSPC-UC-009, BR-RSPC-026, 058)
    WorkflowTransition(
        frm=StaffAppointmentStatus.DRAFT.value,
        to=StaffAppointmentStatus.REQUESTED.value,
        actor_roles=frozenset({RspcRole.FACULTY.value}),
        permission="rspc.staff.request",
        guards=("mandatory_fields_valid",),
        description="Faculty requests project-based staff appointment",
    ),
    # S2: Requested -> Admin Verified (RSPC Admin, RSPC-UC-010, BR-RSPC-026, 066, 070, 058)
    WorkflowTransition(
        frm=StaffAppointmentStatus.REQUESTED.value,
        to=StaffAppointmentStatus.ADMIN_VERIFIED.value,
        actor_roles=frozenset({RspcRole.RSPC_ADMIN.value}),
        permission="rspc.staff.verify",
        guards=("verification_eligible",),
        description="Admin verifies staff appointment request & operational records",
    ),
    # S3: Requested -> Not Eligible (RSPC Admin, RSPC-UC-010, BR-RSPC-066, 070, 058)
    WorkflowTransition(
        frm=StaffAppointmentStatus.REQUESTED.value,
        to=StaffAppointmentStatus.NOT_ELIGIBLE.value,
        actor_roles=frozenset({RspcRole.RSPC_ADMIN.value}),
        permission="rspc.staff.verify",
        guards=("has_remarks",),
        description="Admin marks staff appointment not eligible",
    ),
    # S4: Admin Verified -> Selection Recommended (Faculty, RSPC-UC-022, BR-RSPC-026, 058)
    WorkflowTransition(
        frm=StaffAppointmentStatus.ADMIN_VERIFIED.value,
        to=StaffAppointmentStatus.SELECTION_RECOMMENDED.value,
        actor_roles=frozenset({RspcRole.FACULTY.value}),
        permission="rspc.staff.recommend",
        guards=("has_recommendation",),
        description="Faculty records selection participation and recommendation",
    ),
    # S5: Selection Recommended -> Approved (Dean-RSPC, RSPC-UC-023, BR-RSPC-026, 068, 058)
    WorkflowTransition(
        frm=StaffAppointmentStatus.SELECTION_RECOMMENDED.value,
        to=StaffAppointmentStatus.APPROVED.value,
        actor_roles=frozenset({RspcRole.DEAN_RSPC.value}),
        permission="rspc.staff.approve_dean",
        guards=("within_dean_authority", "has_remarks"),
        description="Dean approves staff appointment",
    ),
    # S6: Selection Recommended -> Forwarded to Director
    # (Dean-RSPC, RSPC-UC-023, BR-RSPC-026, 068, 069)
    WorkflowTransition(
        frm=StaffAppointmentStatus.SELECTION_RECOMMENDED.value,
        to=StaffAppointmentStatus.FORWARDED_TO_DIRECTOR.value,
        actor_roles=frozenset({RspcRole.DEAN_RSPC.value}),
        permission="rspc.staff.approve_dean",
        guards=("requires_director_action", "has_remarks"),
        description="Dean forwards staff appointment to Director",
    ),
    # S7: Selection Recommended -> Dean Not Approved (Dean-RSPC, RSPC-UC-023, BR-RSPC-068, 058)
    WorkflowTransition(
        frm=StaffAppointmentStatus.SELECTION_RECOMMENDED.value,
        to=StaffAppointmentStatus.DEAN_NOT_APPROVED.value,
        actor_roles=frozenset({RspcRole.DEAN_RSPC.value}),
        permission="rspc.staff.approve_dean",
        guards=("has_remarks",),
        description="Dean rejects staff appointment",
    ),
    # S8: Forwarded to Director -> Approved (Director, RSPC-UC-006, BR-RSPC-069, 070, 058)
    WorkflowTransition(
        frm=StaffAppointmentStatus.FORWARDED_TO_DIRECTOR.value,
        to=StaffAppointmentStatus.APPROVED.value,
        actor_roles=frozenset({RspcRole.DIRECTOR.value}),
        permission="rspc.staff.authorize_director",
        guards=("has_remarks",),
        description="Director approves staff appointment",
    ),
    # S9: Forwarded to Director -> Director Not Approved
    # (Director, RSPC-UC-006, BR-RSPC-069, 070, 058)
    WorkflowTransition(
        frm=StaffAppointmentStatus.FORWARDED_TO_DIRECTOR.value,
        to=StaffAppointmentStatus.DIRECTOR_NOT_APPROVED.value,
        actor_roles=frozenset({RspcRole.DIRECTOR.value}),
        permission="rspc.staff.authorize_director",
        guards=("has_remarks",),
        description="Director rejects staff appointment",
    ),
)


# ---------------------------------------------------------------------------
# 4. Financial & Fund Request State Machine (CW-RSPC-04, BW-RSPC-07, BW-RSPC-08)
# ---------------------------------------------------------------------------
FINANCE_TRANSITIONS: tuple[WorkflowTransition, ...] = (
    # S1: Draft -> Submitted (Faculty, RSPC-UC-011, BR-RSPC-059)
    WorkflowTransition(
        frm=FinancialRequestStatus.DRAFT.value,
        to=FinancialRequestStatus.SUBMITTED.value,
        actor_roles=frozenset({RspcRole.FACULTY.value}),
        permission="rspc.finance.request",
        guards=("mandatory_fields_valid", "within_sanctioned_budget"),
        description="Faculty submits fund utilization or expenditure request",
    ),
    # S2: Submitted -> Verified (RSPC Admin, RSPC-UC-012, BR-RSPC-034, 066, 070, 059)
    WorkflowTransition(
        frm=FinancialRequestStatus.SUBMITTED.value,
        to=FinancialRequestStatus.VERIFIED.value,
        actor_roles=frozenset({RspcRole.RSPC_ADMIN.value}),
        permission="rspc.finance.verify",
        guards=("verification_eligible",),
        description="Admin verifies financial request completeness and audit trail",
    ),
    # S3: Submitted -> Not Eligible (RSPC Admin, RSPC-UC-012, BR-RSPC-034, 066, 070, 059)
    WorkflowTransition(
        frm=FinancialRequestStatus.SUBMITTED.value,
        to=FinancialRequestStatus.NOT_ELIGIBLE.value,
        actor_roles=frozenset({RspcRole.RSPC_ADMIN.value}),
        permission="rspc.finance.verify",
        guards=("has_remarks",),
        description="Admin marks financial request not eligible",
    ),
    # S4: Verified -> Approved (Dean-RSPC, RSPC-UC-024, BR-RSPC-032, 034, 068, 059)
    WorkflowTransition(
        frm=FinancialRequestStatus.VERIFIED.value,
        to=FinancialRequestStatus.APPROVED.value,
        actor_roles=frozenset({RspcRole.DEAN_RSPC.value}),
        permission="rspc.finance.approve_dean",
        guards=("within_dean_financial_powers", "has_remarks"),
        description="Dean approves financial request within delegated powers",
    ),
    # S5: Verified -> Forwarded to Director (Dean-RSPC, RSPC-UC-024, BR-RSPC-033, 034, 068, 069)
    WorkflowTransition(
        frm=FinancialRequestStatus.VERIFIED.value,
        to=FinancialRequestStatus.FORWARDED_TO_DIRECTOR.value,
        actor_roles=frozenset({RspcRole.DEAN_RSPC.value}),
        permission="rspc.finance.approve_dean",
        guards=("requires_director_financial_action", "has_remarks"),
        description="Dean forwards high-value financial request to Director",
    ),
    # S6: Verified -> Dean Not Approved (Dean-RSPC, RSPC-UC-024, BR-RSPC-034, 068, 059)
    WorkflowTransition(
        frm=FinancialRequestStatus.VERIFIED.value,
        to=FinancialRequestStatus.DEAN_NOT_APPROVED.value,
        actor_roles=frozenset({RspcRole.DEAN_RSPC.value}),
        permission="rspc.finance.approve_dean",
        guards=("has_remarks",),
        description="Dean rejects financial request",
    ),
    # S7: Forwarded to Director -> Approved (Director, RSPC-UC-006, BR-RSPC-005, 006, 034, 069, 059)
    WorkflowTransition(
        frm=FinancialRequestStatus.FORWARDED_TO_DIRECTOR.value,
        to=FinancialRequestStatus.APPROVED.value,
        actor_roles=frozenset({RspcRole.DIRECTOR.value}),
        permission="rspc.finance.authorize_director",
        guards=("has_remarks",),
        description="Director approves high-value financial request",
    ),
    # S8: Forwarded to Director -> Director Not Approved
    # (Director, RSPC-UC-006, BR-RSPC-034, 069, 059)
    WorkflowTransition(
        frm=FinancialRequestStatus.FORWARDED_TO_DIRECTOR.value,
        to=FinancialRequestStatus.DIRECTOR_NOT_APPROVED.value,
        actor_roles=frozenset({RspcRole.DIRECTOR.value}),
        permission="rspc.finance.authorize_director",
        guards=("has_remarks",),
        description="Director rejects financial request",
    ),
)


# ---------------------------------------------------------------------------
# 5. Procurement Request State Machine (CW-RSPC-05, BW-RSPC-09, BW-RSPC-10)
# ---------------------------------------------------------------------------
PROCUREMENT_TRANSITIONS: tuple[WorkflowTransition, ...] = (
    # S1: Draft -> Submitted (Faculty, RSPC-UC-013, BR-RSPC-035, 060)
    WorkflowTransition(
        frm=ProcurementStatus.DRAFT.value,
        to=ProcurementStatus.SUBMITTED.value,
        actor_roles=frozenset({RspcRole.FACULTY.value}),
        permission="rspc.procurement.request",
        guards=("mandatory_fields_valid", "matches_sanctioned_budget"),
        description="Faculty requests equipment/consumable procurement",
    ),
    # S2: Submitted -> Verified (RSPC Admin, RSPC-UC-025, BR-RSPC-035, 036, 066, 070, 060)
    WorkflowTransition(
        frm=ProcurementStatus.SUBMITTED.value,
        to=ProcurementStatus.VERIFIED.value,
        actor_roles=frozenset({RspcRole.RSPC_ADMIN.value}),
        permission="rspc.procurement.verify",
        guards=("verification_eligible", "matches_sanctioned_budget"),
        description="Admin verifies procurement and confirms budget match",
    ),
    # S3: Submitted -> Not Eligible (RSPC Admin, RSPC-UC-025, BR-RSPC-035, 066, 070, 060)
    WorkflowTransition(
        frm=ProcurementStatus.SUBMITTED.value,
        to=ProcurementStatus.NOT_ELIGIBLE.value,
        actor_roles=frozenset({RspcRole.RSPC_ADMIN.value}),
        permission="rspc.procurement.verify",
        guards=("has_remarks",),
        description="Admin rejects procurement request (e.g. exceeds budget)",
    ),
    # S4: Verified -> Approved (Dean-RSPC, RSPC-UC-026, BR-RSPC-036, 068, 060)
    WorkflowTransition(
        frm=ProcurementStatus.VERIFIED.value,
        to=ProcurementStatus.APPROVED.value,
        actor_roles=frozenset({RspcRole.DEAN_RSPC.value}),
        permission="rspc.procurement.approve_dean",
        guards=("within_dean_procurement_limit", "has_remarks"),
        description="Dean approves procurement within limit",
    ),
    # S5: Verified -> Forwarded to Director (Dean-RSPC, RSPC-UC-026, BR-RSPC-036, 068, 069)
    WorkflowTransition(
        frm=ProcurementStatus.VERIFIED.value,
        to=ProcurementStatus.FORWARDED_TO_DIRECTOR.value,
        actor_roles=frozenset({RspcRole.DEAN_RSPC.value}),
        permission="rspc.procurement.approve_dean",
        guards=("requires_director_procurement_action", "has_remarks"),
        description="Dean forwards high-value procurement to Director",
    ),
    # S6: Verified -> Dean Not Approved (Dean-RSPC, RSPC-UC-026, BR-RSPC-036, 068, 060)
    WorkflowTransition(
        frm=ProcurementStatus.VERIFIED.value,
        to=ProcurementStatus.DEAN_NOT_APPROVED.value,
        actor_roles=frozenset({RspcRole.DEAN_RSPC.value}),
        permission="rspc.procurement.approve_dean",
        guards=("has_remarks",),
        description="Dean rejects procurement request",
    ),
    # S7: Forwarded to Director -> Approved (Director, RSPC-UC-006, BR-RSPC-006, 069, 070, 060)
    WorkflowTransition(
        frm=ProcurementStatus.FORWARDED_TO_DIRECTOR.value,
        to=ProcurementStatus.APPROVED.value,
        actor_roles=frozenset({RspcRole.DIRECTOR.value}),
        permission="rspc.procurement.authorize_director",
        guards=("has_remarks",),
        description="Director approves high-value procurement",
    ),
    # S8: Forwarded to Director -> Director Not Approved (Director, RSPC-UC-006, BR-RSPC-069, 060)
    WorkflowTransition(
        frm=ProcurementStatus.FORWARDED_TO_DIRECTOR.value,
        to=ProcurementStatus.DIRECTOR_NOT_APPROVED.value,
        actor_roles=frozenset({RspcRole.DIRECTOR.value}),
        permission="rspc.procurement.authorize_director",
        guards=("has_remarks",),
        description="Director rejects procurement request",
    ),
)


# ---------------------------------------------------------------------------
# 6. Project Closure State Machine (CW-RSPC-06, BW-RSPC-11, BW-RSPC-12)
# ---------------------------------------------------------------------------
CLOSURE_TRANSITIONS: tuple[WorkflowTransition, ...] = (
    # S1: Draft -> Submitted (Faculty, RSPC-UC-015, BR-RSPC-059, 060)
    WorkflowTransition(
        frm=ClosureStatus.DRAFT.value,
        to=ClosureStatus.SUBMITTED.value,
        actor_roles=frozenset({RspcRole.FACULTY.value}),
        permission="rspc.closure.submit",
        guards=("has_completion_report",),
        description="Faculty submits project closure reports and declarations",
    ),
    # S2: Submitted -> Verified (RSPC Admin, RSPC-UC-027, BR-RSPC-066, 070, 059, 060)
    WorkflowTransition(
        frm=ClosureStatus.SUBMITTED.value,
        to=ClosureStatus.VERIFIED.value,
        actor_roles=frozenset({RspcRole.RSPC_ADMIN.value}),
        permission="rspc.closure.verify",
        guards=("verification_eligible", "settlement_verified", "assets_verified"),
        description="Admin verifies closure completeness and settlement records",
    ),
    # S3: Submitted -> Not Eligible (RSPC Admin, RSPC-UC-027, BR-RSPC-066, 070, 059, 060)
    WorkflowTransition(
        frm=ClosureStatus.SUBMITTED.value,
        to=ClosureStatus.NOT_ELIGIBLE.value,
        actor_roles=frozenset({RspcRole.RSPC_ADMIN.value}),
        permission="rspc.closure.verify",
        guards=("has_remarks",),
        description="Admin marks closure record not eligible for forwarding",
    ),
    # S4: Verified -> Archived (Dean-RSPC, RSPC-UC-028, BR-RSPC-043, 068, 059, 060)
    WorkflowTransition(
        frm=ClosureStatus.VERIFIED.value,
        to=ClosureStatus.ARCHIVED.value,
        actor_roles=frozenset({RspcRole.DEAN_RSPC.value}),
        permission="rspc.closure.approve_dean",
        guards=("within_dean_authority", "has_remarks"),
        description="Dean approves closure and archives completed project with audit trail",
    ),
    # S5: Verified -> Forwarded to Director (Dean-RSPC, RSPC-UC-028, BR-RSPC-068, 069)
    WorkflowTransition(
        frm=ClosureStatus.VERIFIED.value,
        to=ClosureStatus.FORWARDED_TO_DIRECTOR.value,
        actor_roles=frozenset({RspcRole.DEAN_RSPC.value}),
        permission="rspc.closure.approve_dean",
        guards=("requires_director_action", "has_remarks"),
        description="Dean forwards closure to Director",
    ),
    # S6: Verified -> Dean Not Approved (Dean-RSPC, RSPC-UC-028, BR-RSPC-068, 059, 060)
    WorkflowTransition(
        frm=ClosureStatus.VERIFIED.value,
        to=ClosureStatus.DEAN_NOT_APPROVED.value,
        actor_roles=frozenset({RspcRole.DEAN_RSPC.value}),
        permission="rspc.closure.approve_dean",
        guards=("has_remarks",),
        description="Dean rejects project closure",
    ),
    # S7: Forwarded to Director -> Archived (Director, RSPC-UC-006, BR-RSPC-043, 069, 070, 059, 060)
    WorkflowTransition(
        frm=ClosureStatus.FORWARDED_TO_DIRECTOR.value,
        to=ClosureStatus.ARCHIVED.value,
        actor_roles=frozenset({RspcRole.DIRECTOR.value}),
        permission="rspc.closure.authorize_director",
        guards=("has_remarks",),
        description="Director approves closure and archives project",
    ),
    # S8: Forwarded to Director -> Director Not Approved
    # (Director, RSPC-UC-006, BR-RSPC-069, 059, 060)
    WorkflowTransition(
        frm=ClosureStatus.FORWARDED_TO_DIRECTOR.value,
        to=ClosureStatus.DIRECTOR_NOT_APPROVED.value,
        actor_roles=frozenset({RspcRole.DIRECTOR.value}),
        permission="rspc.closure.authorize_director",
        guards=("has_remarks",),
        description="Director rejects project closure",
    ),
)


# ---------------------------------------------------------------------------
# Transition Finder & Evaluator
# ---------------------------------------------------------------------------
def find_transition(
    transitions: tuple[WorkflowTransition, ...],
    from_state: str,
    to_state: str,
    entity_name: str = "record",
) -> WorkflowTransition:
    for t in transitions:
        if t.frm == from_state and t.to == to_state:
            return t
    raise InvalidTransitionError(from_state, to_state, entity_name)


def validate_transition(
    *,
    transitions: tuple[WorkflowTransition, ...],
    from_state: str,
    to_state: str,
    actor_role: str,
    context: dict[str, Any] | None = None,
    entity_name: str = "record",
) -> WorkflowTransition:
    """Validate a transition against state machine rules and guards.
    Pure Python validation function.
    """
    context = context or {}
    t = find_transition(transitions, from_state, to_state, entity_name)

    # Check actor role
    if actor_role not in t.actor_roles and RspcRole.SYSTEM.value not in t.actor_roles:
        raise PermissionDeniedDomainError(actor_role, f"transition to {to_state!r}")

    # Evaluate guards
    for g in t.guards:
        _evaluate_guard(g, context, t)

    return t


def _evaluate_guard(guard_name: str, ctx: dict[str, Any], t: WorkflowTransition) -> None:
    # Remarks guard (BR-RSPC-016)
    if guard_name == "has_remarks":
        remarks = ctx.get("remarks", "")
        if not remarks or not str(remarks).strip():
            raise GuardFailedError("has_remarks", "Remarks are required for this decision.")

    # Recommendation guard
    elif guard_name == "has_recommendation":
        rec = ctx.get("recommendation", "")
        if not rec or not str(rec).strip():
            raise GuardFailedError("has_recommendation", "Selection recommendation is required.")

    # Mandatory fields guard (BR-RSPC-013)
    elif guard_name == "mandatory_fields_valid":
        required = ctx.get("required_fields", [])
        missing = [f for f in required if not ctx.get(f)]
        if missing:
            raise MandatoryFieldMissingError(missing)

    # Policy validation guard (BR-RSPC-014)
    elif guard_name == "policy_validation_passed":
        if not ctx.get("policy_validation_passed", True):
            raise GuardFailedError(
                "policy_validation_passed", "Configured proposal policy validation failed."
            )

    # Admin verification eligible (BR-RSPC-066, BR-RSPC-070)
    elif guard_name == "verification_eligible":
        if not ctx.get("is_eligible", True):
            raise GuardFailedError(
                "verification_eligible",
                "Record does not meet verification completeness/compliance criteria.",
            )

    # Budget match guard (BR-RSPC-035)
    elif guard_name in ("matches_sanctioned_budget", "within_sanctioned_budget"):
        amount = Decimal(str(ctx.get("amount", 0)))
        available = Decimal(str(ctx.get("available_budget", 0)))
        if amount > available:
            raise BudgetExceededError(float(amount), float(available))

    # Dean limits vs Director routing (BR-RSPC-004, 005, 006, 032, 033, 036, 068, 069)
    elif guard_name == "within_dean_authority":
        amount = Decimal(str(ctx.get("budget_amount", 0)))
        threshold = Decimal(
            str(ctx.get("director_funding_threshold", DEFAULT_DIRECTOR_FUNDING_THRESHOLD))
        )
        if amount >= threshold:
            raise GuardFailedError(
                "within_dean_authority",
                f"Proposal amount ({amount}) reaches Director threshold ({threshold}).",
            )

    elif guard_name == "requires_director_action":
        amount = Decimal(str(ctx.get("budget_amount", 0)))
        threshold = Decimal(
            str(ctx.get("director_funding_threshold", DEFAULT_DIRECTOR_FUNDING_THRESHOLD))
        )
        is_strategic = ctx.get("is_strategic", False)
        if amount < threshold and not is_strategic:
            raise GuardFailedError(
                "requires_director_action",
                "Request does not meet Director threshold or strategic criteria.",
            )

    elif guard_name == "within_dean_financial_powers":
        amount = Decimal(str(ctx.get("amount", 0)))
        limit = Decimal(str(ctx.get("dean_financial_limit", DEFAULT_DEAN_FINANCIAL_LIMIT)))
        if amount > limit:
            raise GuardFailedError(
                "within_dean_financial_powers",
                f"Financial amount ({amount}) exceeds Dean limit ({limit}). Forwarding required.",
            )

    elif guard_name == "requires_director_financial_action":
        amount = Decimal(str(ctx.get("amount", 0)))
        limit = Decimal(str(ctx.get("dean_financial_limit", DEFAULT_DEAN_FINANCIAL_LIMIT)))
        if amount <= limit:
            raise GuardFailedError(
                "requires_director_financial_action",
                "Request is within Dean powers and does not require Director escalation.",
            )

    elif guard_name == "within_dean_procurement_limit":
        amount = Decimal(str(ctx.get("estimated_cost", 0)))
        limit = Decimal(str(ctx.get("dean_procurement_limit", DEFAULT_DEAN_PROCUREMENT_LIMIT)))
        if amount > limit:
            raise GuardFailedError(
                "within_dean_procurement_limit",
                f"Procurement cost ({amount}) exceeds Dean limit ({limit}). Forwarding required.",
            )

    elif guard_name == "requires_director_procurement_action":
        amount = Decimal(str(ctx.get("estimated_cost", 0)))
        limit = Decimal(str(ctx.get("dean_procurement_limit", DEFAULT_DEAN_PROCUREMENT_LIMIT)))
        if amount <= limit:
            raise GuardFailedError(
                "requires_director_procurement_action",
                "Procurement is within Dean limit and does not require Director escalation.",
            )

    elif guard_name == "has_completion_report":
        if not ctx.get("completion_report", "").strip():
            raise GuardFailedError(
                "has_completion_report", "Completion report is required for closure submission."
            )

    elif guard_name == "settlement_verified":
        if not ctx.get("settlement_verified", True):
            raise GuardFailedError(
                "settlement_verified", "Financial settlement verification must pass."
            )

    elif guard_name == "assets_verified":
        if not ctx.get("assets_verified", True):
            raise GuardFailedError("assets_verified", "Asset declaration verification must pass.")
