"""Query selectors enforcing ownership, scope, and visibility for Complaint Management System."""
from __future__ import annotations

from typing import Iterable, Sequence
from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from modules.complaints.models import (
    CMSRoleAssignment,
    ClosureVerification,
    Complaint,
    ComplaintAnnouncement,
    ComplaintFeedback,
    ProgressUpdate,
    ReopeningRequest,
    StatusHistoryEntry,
)


def visible_complaints(principal) -> QuerySet[Complaint]:
    """Ownership and role-scope visibility rules for complaints."""
    qs = Complaint.objects.all().select_related("closure_verification", "feedback")

    # If principal has global/module view permission (Supervisor or Handler or Admin)
    if principal.has_perm("complaints.complaint.view"):
        return qs

    # Otherwise restricted to own complaints (Complainant / Student / Faculty / Staff)
    user_id = getattr(principal, "erp_user_id", None) or getattr(principal, "id", None)
    if user_id is not None:
        return qs.filter(complainant_user_id=user_id)

    return qs.none()


def get_complaint_by_id(pk: int, principal=None) -> Complaint | None:
    """Retrieve complaint if visible to the principal."""
    if principal is not None:
        qs = visible_complaints(principal)
    else:
        qs = Complaint.objects.all()
    try:
        return qs.get(pk=pk)
    except Complaint.DoesNotExist:
        return None


def get_complaint_by_code(code: str, principal=None) -> Complaint | None:
    """Retrieve complaint by complaint_id (e.g. CMP-2026-0001)."""
    if principal is not None:
        qs = visible_complaints(principal)
    else:
        qs = Complaint.objects.all()
    try:
        return qs.get(complaint_id=code)
    except Complaint.DoesNotExist:
        return None


def get_assigned_complaints(handler_user_id: int) -> QuerySet[Complaint]:
    """Complaints actively assigned to a specific handler."""
    return Complaint.objects.filter(
        assigned_handler_id=handler_user_id,
    ).exclude(status__in=["closed", "rejected"])


def get_escalated_complaints(principal=None) -> QuerySet[Complaint]:
    """Retrieve escalated complaints."""
    qs = visible_complaints(principal) if principal is not None else Complaint.objects.all()
    return qs.filter(is_escalated=True)


def get_announcements(principal=None, audience: str | None = None) -> QuerySet[ComplaintAnnouncement]:
    """Active announcements matching target audience."""
    now = timezone.now()
    qs = ComplaintAnnouncement.objects.filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    )
    if audience and audience != "all":
        qs = qs.filter(Q(target_audience="all") | Q(target_audience=audience))
    return qs


def get_feedback_list(principal=None) -> QuerySet[ComplaintFeedback]:
    """Feedback list accessible to handlers, supervisors, or admins."""
    return ComplaintFeedback.objects.all().select_related("complaint")


def get_active_role_holder(role_name: str) -> CMSRoleAssignment | None:
    """Get the single active role holder for a CMS role (BR-CMS-037)."""
    return CMSRoleAssignment.objects.filter(
        role_name=role_name,
        is_active=True,
    ).first()


def get_operational_summary() -> dict:
    """Aggregated operational report metrics (AFR-CMS-049..054)."""
    qs = Complaint.objects.all()
    total = qs.count()
    status_counts = dict(qs.values_list("status").annotate(count=Count("id")))
    escalated_count = qs.filter(is_escalated=True).count()
    auto_escalated_count = qs.filter(is_escalated=True, escalation_type="automatic").count()
    manual_escalated_count = qs.filter(is_escalated=True, escalation_type="manual").count()

    return {
        "total_complaints": total,
        "submitted": status_counts.get("submitted", 0),
        "in_progress": status_counts.get("in_progress", 0),
        "resolved": status_counts.get("resolved", 0),
        "rejected": status_counts.get("rejected", 0),
        "closed": status_counts.get("closed", 0),
        "total_escalated": escalated_count,
        "automatic_escalations": auto_escalated_count,
        "manual_escalations": manual_escalated_count,
    }

