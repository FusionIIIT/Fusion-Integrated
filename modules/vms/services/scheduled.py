"""Background tasks and event-triggered services for VMS (UC-037, UC-038)."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from modules.vms.models import VisitRequest


@transaction.atomic
def expire_pending_requests(timeout_hours: int = 24) -> int:
    """Expire pending requests exceeding approval timeout SLA (UC-037, BR-062, BR-200)."""
    cutoff = timezone.now() - timezone.timedelta(hours=timeout_hours)
    expired_visits = VisitRequest.objects.filter(
        status="PENDING_APPROVAL",
        created_at__lt=cutoff,
    )
    count = 0
    for v in expired_visits:
        v.status = "EXPIRED"
        v.save(update_fields=["status", "updated_at"])
        count += 1
    return count


@transaction.atomic
def auto_checkout_overstays(buffer_hours: int = 0) -> int:
    """Automatically checkout on-site visitors who did not exit (UC-038, BR-101)."""
    now = timezone.now()
    cutoff = now - timezone.timedelta(hours=buffer_hours)
    overstay_visits = VisitRequest.objects.filter(
        status="CHECKED_IN",
        scheduled_end__lt=cutoff,
    ).select_related("digital_pass")

    count = 0
    for v in overstay_visits:
        v.status = "AUTO_CHECKED_OUT"
        v.actual_check_out = now
        v.save(update_fields=["status", "actual_check_out", "updated_at"])

        if hasattr(v, "digital_pass"):
            p = v.digital_pass
            p.status = "USED"
            p.save(update_fields=["status", "updated_at"])
        count += 1
    return count
