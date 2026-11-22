from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from modules.vms.models import VisitRequest


def visit_summary(*, starts_at=None, ends_at=None):
    visits = VisitRequest.objects.all()
    if starts_at:
        visits = visits.filter(starts_at__gte=starts_at)
    if ends_at:
        visits = visits.filter(starts_at__lt=ends_at)
    counts = {
        row["status"]: row["count"] for row in visits.values("status").annotate(count=Count("id"))
    }
    return {
        "total": sum(counts.values()),
        "on_site": counts.get("on_site", 0),
        "pending": counts.get("pending", 0),
        "approved": counts.get("approved", 0),
        "rejected": counts.get("rejected", 0),
        "expired": counts.get("expired", 0),
        "completed": counts.get("completed", 0),
        "by_status": counts,
        "generated_at": timezone.now(),
    }


def visitor_export_rows(*, starts_at=None, ends_at=None):
    visits = VisitRequest.objects.select_related("visitor").order_by("starts_at", "pk")
    if starts_at:
        visits = visits.filter(starts_at__gte=starts_at)
    if ends_at:
        visits = visits.filter(starts_at__lt=ends_at)
    return (
        (
            v.pk,
            v.visitor.display_name,
            v.host_user_id,
            v.purpose,
            v.status,
            v.starts_at.isoformat(),
            v.ends_at.isoformat(),
            ",".join(v.approved_zones),
        )
        for v in visits.iterator(chunk_size=500)
    )


def daily_counts(*, starts_at=None, ends_at=None):
    visits = VisitRequest.objects.all()
    if starts_at:
        visits = visits.filter(starts_at__gte=starts_at)
    if ends_at:
        visits = visits.filter(starts_at__lt=ends_at)
    return list(
        visits.annotate(day=TruncDate("starts_at"))
        .values("day", "status")
        .annotate(count=Count("id"))
        .order_by("day", "status")
    )
