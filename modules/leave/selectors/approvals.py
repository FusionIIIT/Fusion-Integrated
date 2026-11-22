"""Read queries for approvals inbox."""
from __future__ import annotations

from django.db.models import Q, QuerySet
from modules.leave.models import LeaveApplication


def get_pending_review_queue(user_id: int) -> QuerySet[LeaveApplication]:
    """Return only work explicitly assigned to this reviewer."""
    qs = LeaveApplication.objects.filter(
        unit_head_user_id=user_id,
        unit_head_reviewed_at__isnull=True,
        status__in=["under_review", "cancel_requested", "extension_requested"],
    )
    qs = qs | LeaveApplication.objects.filter(
        (Q(establishment_user_id=user_id, establishment_reviewed_at__isnull=True)
         | Q(sanctioning_authority_user_id=user_id, establishment_user_id__isnull=True)
         | Q(sanctioning_authority_user_id=user_id, establishment_reviewed_at__isnull=False))
        & (Q(unit_head_reviewed_at__isnull=False) | Q(unit_head_user_id__isnull=True)),
        status__in=["under_review", "cancel_requested", "extension_requested", "resumption_submitted"],
    )
    return qs.distinct().order_by("-created_at")
