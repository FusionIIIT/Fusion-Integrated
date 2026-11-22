from typing import Any
from django.db.models import Count

from modules.pms.models.application import ApplicationStatus, PatentApplication


def get_pms_summary_statistics() -> dict[str, Any]:
    """Calculate institutional-level patent metrics for dashboard and reports (UC-PMS-024)."""
    total = PatentApplication.objects.filter(is_active=True).count()
    granted = PatentApplication.objects.filter(is_active=True, status=ApplicationStatus.GRANTED).count()
    filed = PatentApplication.objects.filter(
        is_active=True,
        status__in=[
            ApplicationStatus.FILED,
            ApplicationStatus.FER_RECEIVED,
            ApplicationStatus.FER_RESPONDED,
            ApplicationStatus.GRANTED,
        ],
    ).count()
    under_review = PatentApplication.objects.filter(
        is_active=True,
        status__in=[ApplicationStatus.SUBMITTED, ApplicationStatus.UNDER_REVIEW],
    ).count()

    status_breakdown = dict(
        PatentApplication.objects.filter(is_active=True)
        .values("status")
        .annotate(count=Count("id"))
        .values_list("status", "count")
    )

    return {
        "total_applications": total,
        "total_granted": granted,
        "total_externally_filed": filed,
        "pending_internal_review": under_review,
        "status_breakdown": status_breakdown,
    }
