"""Application read selectors with ownership filtering.

Enforces:
- Employee sees only their own applications (BR-EL-036).
- Unit Head sees only requests awaiting Unit Head review.
- Establishment sees only requests awaiting establishment routing.
- Sanctioning Authority sees only requests awaiting sanction decision.
- Substitute sees only requests where they are nominated.
"""
from __future__ import annotations

import datetime
from django.db.models import QuerySet

from modules.elm.models import LeaveApplication, LeaveAuditTrail, LeaveCancellationRequest, LeaveExtensionRequest, LeaveResumptionReport


def get_user_applications(employee_id: int) -> QuerySet[LeaveApplication]:
    """Retrieve all leave applications for an employee, ordered newest first."""
    return LeaveApplication.objects.filter(employee_id=employee_id).select_related("leave_type").order_by("-created_at")


def get_application_by_id(application_id: int) -> LeaveApplication | None:
    """Retrieve a single application with related leave type and audit trail."""
    try:
        return LeaveApplication.objects.select_related("leave_type").prefetch_related("audit_trail").get(id=application_id)
    except LeaveApplication.DoesNotExist:
        return None


def get_user_application_or_none(application_id: int, employee_id: int) -> LeaveApplication | None:
    """Retrieve application ensuring caller is the applicant (fail-closed 404)."""
    try:
        return LeaveApplication.objects.select_related("leave_type").get(id=application_id, employee_id=employee_id)
    except LeaveApplication.DoesNotExist:
        return None


def get_pending_substitute_requests(substitute_id: int) -> QuerySet[LeaveApplication]:
    """Retrieve requests awaiting consent from this substitute."""
    return LeaveApplication.objects.filter(
        substitute_id=substitute_id,
        status="AWAITING_SUBSTITUTE",
        substitute_status="PENDING",
    ).select_related("leave_type").order_by("created_at")


def get_pending_for_unit_head(unit_head_id: int | None = None) -> QuerySet[LeaveApplication]:
    """Retrieve applications awaiting Unit Head review."""
    qs = LeaveApplication.objects.filter(status="AWAITING_UNIT_HEAD").select_related("leave_type")
    if unit_head_id is not None:
        qs = qs.exclude(employee_id=unit_head_id)
    return qs.order_by("created_at")


def get_pending_for_establishment() -> QuerySet[LeaveApplication]:
    """Retrieve applications awaiting Establishment verification/routing."""
    return LeaveApplication.objects.filter(status="AWAITING_ESTABLISHMENT").select_related("leave_type").order_by("created_at")


def get_pending_for_sanction(authority_id: int | None = None) -> QuerySet[LeaveApplication]:
    """Retrieve applications awaiting final Sanction decision."""
    qs = LeaveApplication.objects.filter(status="AWAITING_SANCTION").select_related("leave_type")
    if authority_id is not None:
        qs = qs.exclude(employee_id=authority_id)
    return qs.order_by("created_at")


def get_pending_for_director_self_sanction(director_id: int) -> QuerySet[LeaveApplication]:
    """Retrieve self-sanction applications for the Director (BR-EL-020)."""
    return LeaveApplication.objects.filter(
        employee_id=director_id,
        status="AWAITING_DIRECTOR_SELF_SANCTION",
    ).select_related("leave_type").order_by("created_at")


def get_active_leaves_for_employee(employee_id: int) -> QuerySet[LeaveApplication]:
    """Retrieve active pending or approved leaves for overlap checking (BR-EL-012)."""
    active_statuses = [
        "AWAITING_SUBSTITUTE",
        "APPLICANT_ACTION_REQUIRED",
        "AWAITING_UNIT_HEAD",
        "AWAITING_ESTABLISHMENT",
        "AWAITING_SANCTION",
        "AWAITING_DIRECTOR_SELF_SANCTION",
        "APPROVED",
    ]
    return LeaveApplication.objects.filter(employee_id=employee_id, status__in=active_statuses)


def get_pending_cancellations() -> QuerySet[LeaveCancellationRequest]:
    """Retrieve pending pre-start cancellations."""
    return LeaveCancellationRequest.objects.filter(
        status__in=["PENDING_UNIT_HEAD", "PENDING_ESTABLISHMENT", "PENDING_SANCTION"]
    ).select_related("application", "application__leave_type").order_by("created_at")


def get_pending_resumptions() -> QuerySet[LeaveResumptionReport]:
    """Retrieve submitted resumptions awaiting review."""
    return LeaveResumptionReport.objects.filter(status="SUBMITTED").select_related("application", "application__leave_type").order_by("created_at")
