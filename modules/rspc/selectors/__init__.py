"""RSPC selectors — ownership and scope filtering in one place."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.rspc.models import (
    ResearchProject, ConsultancyProject, StaffAppointment,
    FinanceRequest, ProcurementRequest, ProgressReport, ProjectClosure,
)


# ---------------------------------------------------------------------------
# Research Projects
# ---------------------------------------------------------------------------

def visible_proposals(principal) -> QuerySet[ResearchProject]:
    """Return projects visible to the principal.

    - Holders of ``rspc.proposal.view`` see all proposals.
    - Faculty see only their own.
    """
    if principal.has_permission("rspc.proposal.view"):
        return ResearchProject.objects.all()
    return ResearchProject.objects.filter(user_id=principal.user_id)


def get_proposal(proposal_id: int, principal) -> ResearchProject | None:
    return visible_proposals(principal).filter(pk=proposal_id).first()


# ---------------------------------------------------------------------------
# Consultancy Projects
# ---------------------------------------------------------------------------

def visible_consultancy(principal) -> QuerySet[ConsultancyProject]:
    if principal.has_permission("rspc.consultancy.view"):
        return ConsultancyProject.objects.all()
    return ConsultancyProject.objects.filter(user_id=principal.user_id)


def get_consultancy(project_id: int, principal) -> ConsultancyProject | None:
    return visible_consultancy(principal).filter(pk=project_id).first()


# ---------------------------------------------------------------------------
# Staff Appointments
# ---------------------------------------------------------------------------

def visible_appointments(principal) -> QuerySet[StaffAppointment]:
    if principal.has_permission("rspc.appointment.view"):
        return StaffAppointment.objects.select_related("project")
    return StaffAppointment.objects.filter(
        user_id=principal.user_id).select_related("project")


def get_appointment(appointment_id: int, principal) -> StaffAppointment | None:
    return visible_appointments(principal).filter(pk=appointment_id).first()


# ---------------------------------------------------------------------------
# Financial Requests
# ---------------------------------------------------------------------------

def visible_finance(principal) -> QuerySet[FinanceRequest]:
    if principal.has_permission("rspc.finance.view"):
        return FinanceRequest.objects.select_related("project")
    return FinanceRequest.objects.filter(
        user_id=principal.user_id).select_related("project")


def get_finance(request_id: int, principal) -> FinanceRequest | None:
    return visible_finance(principal).filter(pk=request_id).first()


# ---------------------------------------------------------------------------
# Procurement Requests
# ---------------------------------------------------------------------------

def visible_procurement(principal) -> QuerySet[ProcurementRequest]:
    if principal.has_permission("rspc.procurement.view"):
        return ProcurementRequest.objects.select_related("project")
    return ProcurementRequest.objects.filter(
        user_id=principal.user_id).select_related("project")


def get_procurement(request_id: int, principal) -> ProcurementRequest | None:
    return visible_procurement(principal).filter(pk=request_id).first()


# ---------------------------------------------------------------------------
# Progress Reports
# ---------------------------------------------------------------------------

def visible_progress_reports(principal) -> QuerySet[ProgressReport]:
    if principal.has_permission("rspc.progress_report.view"):
        return ProgressReport.objects.select_related("project")
    return ProgressReport.objects.filter(
        user_id=principal.user_id).select_related("project")


def get_progress_report(report_id: int, principal) -> ProgressReport | None:
    return visible_progress_reports(principal).filter(pk=report_id).first()


# ---------------------------------------------------------------------------
# Project Closures
# ---------------------------------------------------------------------------

def visible_closures(principal) -> QuerySet[ProjectClosure]:
    if principal.has_permission("rspc.closure.view"):
        return ProjectClosure.objects.select_related("project")
    return ProjectClosure.objects.filter(
        user_id=principal.user_id).select_related("project")


def get_closure(closure_id: int, principal) -> ProjectClosure | None:
    return visible_closures(principal).filter(pk=closure_id).first()
