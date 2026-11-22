"""Read-only selectors for visitor analytics and statistics."""

from __future__ import annotations

from django.utils import timezone

from modules.vms.models import VisitRequest


def get_dashboard_metrics() -> dict[str, int]:
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_today = VisitRequest.objects.filter(scheduled_start__gte=today_start).count()
    onsite_count = VisitRequest.objects.filter(status="CHECKED_IN").count()
    approved_count = VisitRequest.objects.filter(status="APPROVED").count()
    pending_count = VisitRequest.objects.filter(status="PENDING_APPROVAL").count()
    rejected_count = VisitRequest.objects.filter(status="REJECTED").count()
    overstay_count = VisitRequest.objects.filter(status="AUTO_CHECKED_OUT").count()
    total_completed = VisitRequest.objects.filter(status="CHECKED_OUT").count()

    return {
        "total_today": total_today,
        "onsite_now": onsite_count,
        "approved": approved_count,
        "pending": pending_count,
        "rejected": rejected_count,
        "overstays": overstay_count,
        "completed": total_completed,
    }
