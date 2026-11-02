"""Selectors for querying complaint data with scope and permission enforcement."""
from typing import Any, Dict, Optional
from django.db.models import Avg, Count, F, Q, QuerySet
from django.utils import timezone

from modules.complaints.models import (
    CmsRoleAssignment,
    Complaint,
    ComplaintAnnouncement,
    ComplaintCategory,
    ComplaintFeedback,
)


def visible_complaints(principal: Any, **filters: Any) -> QuerySet[Complaint]:
    """Return complaints visible to the calling principal.

    - Complaint Handlers, Supervisors and Admins see all complaints.
    - Regular Users / Complainants see only complaints they submitted.
    """
    qs = Complaint.objects.select_related("category").prefetch_related("attachments", "transitions")

    has_broad_view = (
        getattr(principal, "kind", None) == "admin"
        or getattr(principal, "active_role", None) in ("admin", "complaint_handler", "complaint_supervisor")
        or principal.has_any_permission(
            "complaints.complaint.view",
            "complaints.complaint.supervise",
            "complaints.complaint.assign",
        )
    )

    if not has_broad_view:
        uid = getattr(principal, "user_id", None) or getattr(principal, "erp_user_id", None)
        qs = qs.filter(complainant_user_id=uid)

    # Optional filters
    if status := filters.get("status"):
        qs = qs.filter(status=status)
    if priority := filters.get("priority"):
        qs = qs.filter(priority=priority)
    if category_id := filters.get("category_id"):
        qs = qs.filter(category_id=category_id)
    if is_escalated := filters.get("is_escalated"):
        qs = qs.filter(is_escalated=(is_escalated in (True, "true", "1")))
    if search := filters.get("search"):
        qs = qs.filter(
            Q(complaint_id__icontains=search)
            | Q(location__icontains=search)
            | Q(description__icontains=search)
        )

    return qs


def get_complaint_by_id(pk: int | str, principal: Any) -> Optional[Complaint]:
    """Retrieve a single complaint ensuring visibility scope."""
    qs = visible_complaints(principal)
    if isinstance(pk, int) or str(pk).isdigit():
        return qs.filter(pk=int(pk)).first()
    return qs.filter(complaint_id=str(pk)).first()


def escalated_complaints(principal: Any) -> QuerySet[Complaint]:
    """Return escalated complaints for supervisory oversight."""
    return visible_complaints(principal, is_escalated=True)


def pending_reopenings(principal: Any) -> QuerySet[Complaint]:
    """Return complaints awaiting reopening review."""
    return visible_complaints(principal).filter(reopening_status="pending")


def verification_queue(principal: Any) -> QuerySet[Complaint]:
    """Return resolved complaints awaiting closure verification."""
    return visible_complaints(principal).filter(
        status="resolved",
        verification_required__in=["user", "supervisor"],
    )


def get_complaint_reports_summary() -> Dict[str, Any]:
    """Compute aggregate statistics for CMS reports and operational dashboards."""
    now = timezone.now()
    qs = Complaint.objects.all()

    total = qs.count()
    by_status = dict(qs.values_list("status").annotate(count=Count("id")))
    by_priority = dict(qs.values_list("priority").annotate(count=Count("id")))
    by_category = list(
        ComplaintCategory.objects.annotate(count=Count("complaints")).values("id", "name", "count")
    )

    escalated_count = qs.filter(is_escalated=True).count()
    breached_count = qs.filter(
        ~Q(status__in=["resolved", "closed", "rejected"]),
        sla_deadline__lt=now,
    ).count()

    feedbacks = ComplaintFeedback.objects.aggregate(avg_rating=Avg("rating"), total_reviews=Count("id"))

    return {
        "total_complaints": total,
        "by_status": by_status,
        "by_priority": by_priority,
        "by_category": by_category,
        "escalated_count": escalated_count,
        "sla_breached_count": breached_count,
        "average_rating": round(feedbacks["avg_rating"] or 0.0, 2),
        "total_feedback": feedbacks["total_reviews"],
    }


def visible_announcements(category_id: Optional[int] = None) -> QuerySet[ComplaintAnnouncement]:
    """Return active announcements visible to users."""
    qs = ComplaintAnnouncement.objects.filter(is_active=True).select_related("category")
    if category_id:
        qs = qs.filter(Q(category_id=category_id) | Q(category__isnull=True))
    return qs


def get_active_cms_roles() -> Dict[str, Optional[CmsRoleAssignment]]:
    """Return current active handler and supervisor role assignments."""
    now = timezone.now()
    handler = (
        CmsRoleAssignment.objects.filter(
            role_type=CmsRoleAssignment.ROLE_HANDLER,
            is_active=True,
            start_date__lte=now,
            end_date__gte=now,
        )
        .order_by("-created_at")
        .first()
    )
    supervisor = (
        CmsRoleAssignment.objects.filter(
            role_type=CmsRoleAssignment.ROLE_SUPERVISOR,
            is_active=True,
            start_date__lte=now,
            end_date__gte=now,
        )
        .order_by("-created_at")
        .first()
    )
    return {
        "handler": handler,
        "supervisor": supervisor,
    }
