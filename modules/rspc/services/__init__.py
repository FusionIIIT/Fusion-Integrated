"""RSPC services — all writes go through here.

Each service function:
  - Uses select_for_update() to prevent concurrent transitions.
  - Calls validate_transition() from domain (raises domain errors only).
  - Creates a Transition audit row.
  - Saves with update_fields (no accidental overwrites).
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.rspc import selectors
from modules.rspc.domain.state_machine import (
    PROPOSAL_TRANSITIONS, CONSULTANCY_TRANSITIONS,
    APPOINTMENT_TRANSITIONS, FINANCE_TRANSITIONS,
    PROCUREMENT_TRANSITIONS, PROGRESS_REPORT_TRANSITIONS,
    CLOSURE_TRANSITIONS,
    validate_transition,
    ProposalStatus, ConsultancyStatus, AppointmentStatus,
    FinanceStatus, ProcurementStatus, ProgressReportStatus, ClosureStatus,
)
from modules.rspc.models import (
    ResearchProject, ResearchProjectTransition,
    ConsultancyProject, ConsultancyTransition,
    StaffAppointment, AppointmentTransition,
    FinanceRequest, FinanceTransition,
    ProcurementRequest, ProcurementTransition,
    ProgressReport, ProgressReportTransition,
    ProjectClosure, ClosureTransition,
)


def _perms(principal) -> set[str]:
    """Return the set of permission codes held by the principal."""
    return set(getattr(principal, "permissions", []) or [])


# ===========================================================================
# Research Project Proposals
# ===========================================================================

PROPOSAL_EDITABLE = (
    "title", "objectives", "funding_source", "budget_requested",
    "start_date", "end_date", "resource_requirements", "department",
)


@transaction.atomic
def create_proposal(*, principal, **fields) -> ResearchProject:
    data = {k: v for k, v in fields.items() if k in PROPOSAL_EDITABLE}
    return ResearchProject.objects.create(
        user_id=principal.user_id,
        status=ProposalStatus.DRAFT,
        **data,
    )


@transaction.atomic
def update_proposal(*, proposal_id: int, principal, **fields) -> ResearchProject:
    obj = selectors.get_proposal(proposal_id, principal)
    if obj is None:
        raise NotFoundError("Proposal not found.")
    if obj.status != ProposalStatus.DRAFT:
        raise ConflictError("Only draft proposals can be edited.",
                            code="not_draft")
    for k, v in fields.items():
        if k in PROPOSAL_EDITABLE:
            setattr(obj, k, v)
    obj.save(update_fields=[*PROPOSAL_EDITABLE, "updated_at"])
    return obj


@transaction.atomic
def transition_proposal(
    *, proposal_id: int, to_status: str, principal,
    remarks: str = "",
) -> ResearchProject:
    obj = ResearchProject.objects.select_for_update().filter(pk=proposal_id).first()
    if obj is None:
        raise NotFoundError("Proposal not found.")

    # Build guard context
    ctx = {
        "mandatory_fields_present": bool(obj.title and obj.objectives
                                         and obj.funding_source),
        "has_remarks": bool(remarks),
        "completeness_check": bool(obj.title and obj.funding_source),
    }
    t = validate_transition(PROPOSAL_TRANSITIONS, obj.status, to_status,
                            _perms(principal), ctx)

    frm = obj.status
    obj.status = to_status
    now = timezone.now()

    # Set stage timestamps
    if to_status == ProposalStatus.SUBMITTED:
        obj.submitted_at = now
    elif to_status in (ProposalStatus.HOD_RECOMMENDED,
                       ProposalStatus.HOD_NOT_RECOMMENDED):
        obj.hod_decided_at = now
        obj.hod_remarks = remarks
    elif to_status == ProposalStatus.ADMIN_VERIFIED:
        obj.admin_verified_at = now
        obj.admin_remarks = remarks
    elif to_status in (ProposalStatus.DEAN_APPROVED,
                       ProposalStatus.DEAN_REJECTED,
                       ProposalStatus.FORWARDED_DIRECTOR):
        obj.dean_decided_at = now
        obj.dean_remarks = remarks
    elif to_status in (ProposalStatus.DIRECTOR_APPROVED,
                       ProposalStatus.DIRECTOR_REJECTED):
        obj.director_decided_at = now
        obj.director_remarks = remarks

    obj.save(update_fields=["status", "hod_decided_at", "hod_remarks",
                             "admin_verified_at", "admin_remarks",
                             "dean_decided_at", "dean_remarks",
                             "director_decided_at", "director_remarks",
                             "submitted_at", "updated_at"])

    ResearchProjectTransition.objects.create(
        project=obj, from_status=frm, to_status=to_status,
        actor_user_id=principal.user_id, remarks=remarks,
    )
    return obj


# ===========================================================================
# Consultancy Projects
# ===========================================================================

CONSULTANCY_EDITABLE = (
    "title", "client_name", "client_details", "scope", "deliverables",
    "financial_terms", "total_amount", "start_date", "end_date", "department",
)


@transaction.atomic
def create_consultancy(*, principal, **fields) -> ConsultancyProject:
    data = {k: v for k, v in fields.items() if k in CONSULTANCY_EDITABLE}
    return ConsultancyProject.objects.create(
        user_id=principal.user_id,
        status=ConsultancyStatus.DRAFT,
        **data,
    )


@transaction.atomic
def update_consultancy(*, project_id: int, principal, **fields) -> ConsultancyProject:
    obj = selectors.get_consultancy(project_id, principal)
    if obj is None:
        raise NotFoundError("Consultancy project not found.")
    if obj.status != ConsultancyStatus.DRAFT:
        raise ConflictError("Only draft consultancy projects can be edited.",
                            code="not_draft")
    for k, v in fields.items():
        if k in CONSULTANCY_EDITABLE:
            setattr(obj, k, v)
    obj.save(update_fields=[*CONSULTANCY_EDITABLE, "updated_at"])
    return obj


@transaction.atomic
def transition_consultancy(
    *, project_id: int, to_status: str, principal, remarks: str = "",
) -> ConsultancyProject:
    obj = ConsultancyProject.objects.select_for_update().filter(pk=project_id).first()
    if obj is None:
        raise NotFoundError("Consultancy project not found.")

    ctx = {
        "mandatory_fields_present": bool(obj.title and obj.client_name),
        "has_remarks": bool(remarks),
    }
    validate_transition(CONSULTANCY_TRANSITIONS, obj.status, to_status,
                        _perms(principal), ctx)

    frm = obj.status
    obj.status = to_status
    now = timezone.now()
    if to_status == ConsultancyStatus.SUBMITTED:
        obj.submitted_at = now
    elif to_status in (ConsultancyStatus.HOD_RECOMMENDED,):
        obj.hod_decided_at = now
        obj.hod_remarks = remarks
    elif to_status == ConsultancyStatus.ADMIN_VERIFIED:
        obj.admin_verified_at = now
        obj.admin_remarks = remarks
    elif to_status in (ConsultancyStatus.DEAN_APPROVED,
                       ConsultancyStatus.DEAN_REJECTED,
                       ConsultancyStatus.FORWARDED_DIRECTOR):
        obj.dean_decided_at = now
        obj.dean_remarks = remarks
    elif to_status in (ConsultancyStatus.DIRECTOR_APPROVED,
                       ConsultancyStatus.DIRECTOR_REJECTED):
        obj.director_decided_at = now
        obj.director_remarks = remarks

    obj.save(update_fields=["status", "hod_decided_at", "hod_remarks",
                             "admin_verified_at", "admin_remarks",
                             "dean_decided_at", "dean_remarks",
                             "director_decided_at", "director_remarks",
                             "submitted_at", "updated_at"])
    ConsultancyTransition.objects.create(
        consultancy=obj, from_status=frm, to_status=to_status,
        actor_user_id=principal.user_id, remarks=remarks,
    )
    return obj


# ===========================================================================
# Staff Appointments
# ===========================================================================

APPOINTMENT_EDITABLE = (
    "position_title", "stipend_amount", "duration_months", "department",
)


@transaction.atomic
def create_appointment(*, principal, project_id: int | None = None,
                       **fields) -> StaffAppointment:
    data = {k: v for k, v in fields.items() if k in APPOINTMENT_EDITABLE}
    if project_id:
        data["project_id"] = project_id
    return StaffAppointment.objects.create(
        user_id=principal.user_id,
        status=AppointmentStatus.DRAFT,
        **data,
    )


@transaction.atomic
def transition_appointment(
    *, appointment_id: int, to_status: str, principal, remarks: str = "",
) -> StaffAppointment:
    obj = StaffAppointment.objects.select_for_update().filter(
        pk=appointment_id).first()
    if obj is None:
        raise NotFoundError("Appointment request not found.")

    ctx = {
        "mandatory_fields_present": bool(obj.position_title),
        "has_remarks": bool(remarks),
    }
    validate_transition(APPOINTMENT_TRANSITIONS, obj.status, to_status,
                        _perms(principal), ctx)

    frm = obj.status
    obj.status = to_status
    now = timezone.now()
    if to_status == AppointmentStatus.REQUESTED:
        obj.submitted_at = now
    elif to_status == AppointmentStatus.ADMIN_VERIFIED:
        obj.admin_verified_at = now
        obj.admin_remarks = remarks
    elif to_status == AppointmentStatus.SELECTION_RECOMMENDATION:
        obj.selection_remarks = remarks
    elif to_status in (AppointmentStatus.APPROVED,
                       AppointmentStatus.FORWARDED_DIRECTOR):
        obj.dean_decided_at = now
        obj.dean_remarks = remarks
    elif to_status in (AppointmentStatus.DIRECTOR_APPROVED,
                       AppointmentStatus.REJECTED):
        obj.director_decided_at = now
        obj.director_remarks = remarks

    obj.save(update_fields=["status", "submitted_at", "admin_verified_at",
                             "admin_remarks", "selection_remarks",
                             "dean_decided_at", "dean_remarks",
                             "director_decided_at", "director_remarks",
                             "updated_at"])
    AppointmentTransition.objects.create(
        appointment=obj, from_status=frm, to_status=to_status,
        actor_user_id=principal.user_id, remarks=remarks,
    )
    return obj


# ===========================================================================
# Financial Requests
# ===========================================================================

FINANCE_EDITABLE = ("category", "description", "amount", "purpose")


@transaction.atomic
def create_finance_request(*, principal, project_id: int | None = None,
                           **fields) -> FinanceRequest:
    data = {k: v for k, v in fields.items() if k in FINANCE_EDITABLE}
    if project_id:
        data["project_id"] = project_id
    return FinanceRequest.objects.create(
        user_id=principal.user_id,
        status=FinanceStatus.DRAFT,
        **data,
    )


@transaction.atomic
def transition_finance(
    *, request_id: int, to_status: str, principal, remarks: str = "",
) -> FinanceRequest:
    obj = FinanceRequest.objects.select_for_update().filter(pk=request_id).first()
    if obj is None:
        raise NotFoundError("Financial request not found.")

    ctx = {
        "mandatory_fields_present": bool(obj.description and obj.amount),
        "has_remarks": bool(remarks),
    }
    validate_transition(FINANCE_TRANSITIONS, obj.status, to_status,
                        _perms(principal), ctx)

    frm = obj.status
    obj.status = to_status
    now = timezone.now()
    if to_status == FinanceStatus.SUBMITTED:
        obj.submitted_at = now
    elif to_status == FinanceStatus.VERIFIED:
        obj.admin_verified_at = now
        obj.admin_remarks = remarks
    elif to_status in (FinanceStatus.APPROVED, FinanceStatus.REJECTED,
                       FinanceStatus.FORWARDED_DIRECTOR):
        obj.dean_decided_at = now
        obj.dean_remarks = remarks
    elif to_status in (FinanceStatus.DIRECTOR_APPROVED,):
        obj.director_decided_at = now
        obj.director_remarks = remarks

    obj.save(update_fields=["status", "submitted_at", "admin_verified_at",
                             "admin_remarks", "dean_decided_at", "dean_remarks",
                             "director_decided_at", "director_remarks",
                             "updated_at"])
    FinanceTransition.objects.create(
        request=obj, from_status=frm, to_status=to_status,
        actor_user_id=principal.user_id, remarks=remarks,
    )
    return obj


# ===========================================================================
# Procurement Requests
# ===========================================================================

PROCUREMENT_EDITABLE = (
    "item_description", "quantity", "estimated_cost", "justification",
)


@transaction.atomic
def create_procurement_request(*, principal, project_id: int | None = None,
                                **fields) -> ProcurementRequest:
    data = {k: v for k, v in fields.items() if k in PROCUREMENT_EDITABLE}
    if project_id:
        data["project_id"] = project_id
    return ProcurementRequest.objects.create(
        user_id=principal.user_id,
        status=ProcurementStatus.DRAFT,
        **data,
    )


@transaction.atomic
def transition_procurement(
    *, request_id: int, to_status: str, principal, remarks: str = "",
) -> ProcurementRequest:
    obj = ProcurementRequest.objects.select_for_update().filter(
        pk=request_id).first()
    if obj is None:
        raise NotFoundError("Procurement request not found.")

    # Check budget availability for VERIFIED state
    budget_ok = True
    if to_status == ProcurementStatus.VERIFIED and obj.project_id:
        project = obj.project
        if project and project.budget_requested is not None:
            spent = ProcurementRequest.objects.filter(
                project=project,
                status__in=[ProcurementStatus.VERIFIED,
                            ProcurementStatus.APPROVED,
                            ProcurementStatus.DIRECTOR_APPROVED],
            ).exclude(pk=obj.pk).values_list(
                "estimated_cost", flat=True)
            total_spent = sum(spent) if spent else 0
            budget_ok = (total_spent + obj.estimated_cost
                         <= project.budget_requested)

    ctx = {
        "mandatory_fields_present": bool(obj.item_description),
        "has_remarks": bool(remarks),
        "budget_check": budget_ok,
    }
    validate_transition(PROCUREMENT_TRANSITIONS, obj.status, to_status,
                        _perms(principal), ctx)

    frm = obj.status
    obj.status = to_status
    now = timezone.now()
    if to_status == ProcurementStatus.SUBMITTED:
        obj.submitted_at = now
    elif to_status == ProcurementStatus.VERIFIED:
        obj.admin_verified_at = now
        obj.admin_remarks = remarks
    elif to_status in (ProcurementStatus.APPROVED, ProcurementStatus.REJECTED,
                       ProcurementStatus.FORWARDED_DIRECTOR):
        obj.dean_decided_at = now
        obj.dean_remarks = remarks
    elif to_status == ProcurementStatus.DIRECTOR_APPROVED:
        obj.director_decided_at = now
        obj.director_remarks = remarks

    obj.save(update_fields=["status", "submitted_at", "admin_verified_at",
                             "admin_remarks", "dean_decided_at", "dean_remarks",
                             "director_decided_at", "director_remarks",
                             "updated_at"])
    ProcurementTransition.objects.create(
        request=obj, from_status=frm, to_status=to_status,
        actor_user_id=principal.user_id, remarks=remarks,
    )
    return obj


# ===========================================================================
# Progress Reports
# ===========================================================================

PROGRESS_REPORT_EDITABLE = (
    "reporting_period", "summary", "milestones_achieved", "expenditure_so_far",
)


@transaction.atomic
def create_progress_report(*, principal, project_id: int, **fields) -> ProgressReport:
    data = {k: v for k, v in fields.items() if k in PROGRESS_REPORT_EDITABLE}
    return ProgressReport.objects.create(
        user_id=principal.user_id,
        project_id=project_id,
        status=ProgressReportStatus.DRAFT,
        **data,
    )


@transaction.atomic
def transition_progress_report(
    *, report_id: int, to_status: str, principal, remarks: str = "",
) -> ProgressReport:
    obj = ProgressReport.objects.select_for_update().filter(pk=report_id).first()
    if obj is None:
        raise NotFoundError("Progress report not found.")

    ctx = {
        "mandatory_fields_present": bool(obj.reporting_period and obj.summary),
        "has_remarks": bool(remarks),
    }
    validate_transition(PROGRESS_REPORT_TRANSITIONS, obj.status, to_status,
                        _perms(principal), ctx)

    frm = obj.status
    obj.status = to_status
    now = timezone.now()
    if to_status == ProgressReportStatus.SUBMITTED:
        obj.submitted_at = now
    elif to_status in (ProgressReportStatus.ACCEPTED,
                       ProgressReportStatus.RETURNED):
        obj.reviewed_at = now
        obj.reviewer_remarks = remarks

    obj.save(update_fields=["status", "submitted_at", "reviewed_at",
                             "reviewer_remarks", "updated_at"])
    ProgressReportTransition.objects.create(
        report=obj, from_status=frm, to_status=to_status,
        actor_user_id=principal.user_id, remarks=remarks,
    )
    return obj


# ===========================================================================
# Project Closures
# ===========================================================================

CLOSURE_EDITABLE = (
    "completion_summary", "financial_settlement_details", "assets_declared",
)


@transaction.atomic
def create_closure(*, principal, project_id: int, **fields) -> ProjectClosure:
    data = {k: v for k, v in fields.items() if k in CLOSURE_EDITABLE}
    return ProjectClosure.objects.create(
        user_id=principal.user_id,
        project_id=project_id,
        status=ClosureStatus.DRAFT,
        **data,
    )


@transaction.atomic
def transition_closure(
    *, closure_id: int, to_status: str, principal, remarks: str = "",
) -> ProjectClosure:
    obj = ProjectClosure.objects.select_for_update().filter(pk=closure_id).first()
    if obj is None:
        raise NotFoundError("Closure record not found.")

    ctx = {
        "mandatory_fields_present": bool(obj.completion_summary),
        "has_remarks": bool(remarks),
    }
    validate_transition(CLOSURE_TRANSITIONS, obj.status, to_status,
                        _perms(principal), ctx)

    frm = obj.status
    obj.status = to_status
    now = timezone.now()
    if to_status == ClosureStatus.SUBMITTED:
        obj.submitted_at = now
    elif to_status == ClosureStatus.ADMIN_VERIFIED:
        obj.admin_verified_at = now
        obj.admin_remarks = remarks
    elif to_status in (ClosureStatus.DEAN_APPROVED, ClosureStatus.DEAN_REJECTED):
        obj.dean_decided_at = now
        obj.dean_remarks = remarks

    obj.save(update_fields=["status", "submitted_at", "admin_verified_at",
                             "admin_remarks", "dean_decided_at", "dean_remarks",
                             "updated_at"])
    ClosureTransition.objects.create(
        closure=obj, from_status=frm, to_status=to_status,
        actor_user_id=principal.user_id, remarks=remarks,
    )
    return obj
