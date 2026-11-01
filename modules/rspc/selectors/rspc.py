"""RSPC Read Selectors.
Follows the Fusion ERP rule: All reads and ownership scoping live HERE, once per module.
An unauthorized ID naturally yields 404/Empty instead of data leakage.
"""

from __future__ import annotations

from django.db.models import QuerySet

from modules.rspc.models import (
    ConsultancyMilestoneSettlement,
    ConsultancyProject,
    ExternalAgencyTracking,
    FinancialRequest,
    ProcurementRequest,
    ProgressReport,
    ProjectClosureRecord,
    ResearchProposal,
    RSPCAuditTrail,
    RSPCNotification,
    RSPCProject,
    StaffAppointmentRequest,
)


def visible_proposals(principal) -> QuerySet[ResearchProposal]:
    """Return proposals visible to the principal."""
    qs = ResearchProposal.objects.all()
    if principal is None:
        return qs.none()
    if principal.has_permission("rspc.proposal.view"):
        return qs
    return qs.filter(faculty_user_id=principal.user_id)


def visible_consultancies(principal) -> QuerySet[ConsultancyProject]:
    """Return consultancy projects visible to the principal."""
    qs = ConsultancyProject.objects.all()
    if principal is None:
        return qs.none()
    if principal.has_permission("rspc.consultancy.view"):
        return qs
    return qs.filter(faculty_user_id=principal.user_id)


def visible_projects(principal) -> QuerySet[RSPCProject]:
    """Return active/completed/archived institutional projects visible to the principal (UC-001)."""
    qs = RSPCProject.objects.all()
    if principal is None:
        return qs.none()
    if principal.has_permission("rspc.project.view"):
        return qs
    return qs.filter(pi_user_id=principal.user_id)


def visible_consultancy_settlements(
    principal, consultancy_id: int | None = None
) -> QuerySet[ConsultancyMilestoneSettlement]:
    """Return consultancy milestone settlements (UC-008)."""
    qs = ConsultancyMilestoneSettlement.objects.select_related("consultancy")
    if consultancy_id:
        qs = qs.filter(consultancy_id=consultancy_id)
    if principal is None:
        return qs.none()
    if principal.has_permission("rspc.consultancy.view"):
        return qs
    return qs.filter(consultancy__faculty_user_id=principal.user_id)


def visible_staff_appointments(
    principal, project_id: int | None = None
) -> QuerySet[StaffAppointmentRequest]:
    """Return staff appointment requests visible to the principal (PS 3.3)."""
    qs = StaffAppointmentRequest.objects.select_related("project")
    if project_id:
        qs = qs.filter(project_id=project_id)
    if principal is None:
        return qs.none()
    if principal.has_permission("rspc.staff.view"):
        return qs
    return qs.filter(faculty_user_id=principal.user_id)


def visible_financial_requests(
    principal, project_id: int | None = None
) -> QuerySet[FinancialRequest]:
    """Return financial/fund requests visible to the principal (PS 3.4)."""
    qs = FinancialRequest.objects.select_related("project")
    if project_id:
        qs = qs.filter(project_id=project_id)
    if principal is None:
        return qs.none()
    if principal.has_permission("rspc.finance.view"):
        return qs
    return qs.filter(faculty_user_id=principal.user_id)


def visible_procurement_requests(
    principal, project_id: int | None = None
) -> QuerySet[ProcurementRequest]:
    """Return equipment/consumables procurement requests visible to principal (PS 3.5)."""
    qs = ProcurementRequest.objects.select_related("project")
    if project_id:
        qs = qs.filter(project_id=project_id)
    if principal is None:
        return qs.none()
    if principal.has_permission("rspc.procurement.view"):
        return qs
    return qs.filter(faculty_user_id=principal.user_id)


def visible_progress_reports(principal, project_id: int | None = None) -> QuerySet[ProgressReport]:
    """Return progress and utilization reports visible to principal (BR-RSPC-038, BR-RSPC-039)."""
    qs = ProgressReport.objects.select_related("project")
    if project_id:
        qs = qs.filter(project_id=project_id)
    if principal is None:
        return qs.none()
    if principal.has_permission("rspc.report.view"):
        return qs
    return qs.filter(faculty_user_id=principal.user_id)


def visible_closure_records(
    principal, project_id: int | None = None
) -> QuerySet[ProjectClosureRecord]:
    """Return project closure records visible to principal (PS 3.7)."""
    qs = ProjectClosureRecord.objects.select_related("project")
    if project_id:
        qs = qs.filter(project_id=project_id)
    if principal is None:
        return qs.none()
    if principal.has_any_permission(
        "rspc.closure.approve_dean", "rspc.closure.verify", "rspc.project.view"
    ):
        return qs
    return qs.filter(faculty_user_id=principal.user_id)


def visible_notifications(principal) -> QuerySet[RSPCNotification]:
    """Return in-app notifications for the logged in principal (UC-016)."""
    if principal is None:
        return RSPCNotification.objects.none()
    return RSPCNotification.objects.filter(recipient_user_id=principal.user_id).order_by(
        "-created_at"
    )


def visible_audit_trails(
    principal, record_type: str | None = None, record_id: int | None = None
) -> QuerySet[RSPCAuditTrail]:
    """Return audit trail records (BR-RSPC-050, UC-017)."""
    qs = RSPCAuditTrail.objects.all().order_by("-timestamp")
    if record_type:
        qs = qs.filter(record_type=record_type)
    if record_id:
        qs = qs.filter(record_id=record_id)
    if principal is None:
        return qs.none()
    if principal.has_permission("rspc.audit.view"):
        return qs
    # Faculty sees audits on their own actions/records
    return qs.filter(actor_user_id=principal.user_id)


def visible_agency_trackings(
    principal, project_id: int | None = None
) -> QuerySet[ExternalAgencyTracking]:
    """Return funding agency tracking updates (UC-030)."""
    qs = ExternalAgencyTracking.objects.all()
    if project_id:
        qs = qs.filter(project_id=project_id)
    if principal is None:
        return qs.none()
    if principal.has_any_permission("rspc.agency.track", "rspc.project.view"):
        return qs
    return qs.filter(project__pi_user_id=principal.user_id)
