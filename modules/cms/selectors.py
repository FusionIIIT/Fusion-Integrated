"""Read paths with ownership scoping applied before data is returned."""

from django.db.models import Q

from modules.cms.models import CmsRoleAssignment, Complaint


def complaints_for(actor, *, staff=False):
    qs = Complaint.objects.all().prefetch_related(
        "attachments", "history", "progress_updates", "reopening_requests"
    )
    if not staff:
        return qs.filter(complainant_user_id=actor.user_id)
    return qs.filter(
        Q(complainant_user_id=actor.user_id)
        | Q(assigned_handler_user_id=actor.user_id)
        | Q(status__in=["submitted", "in_progress", "resolved", "rejected", "closed"])
    )


def has_active_role(user_id: int, role: str, *, at=None) -> bool:
    from django.utils import timezone

    at = at or timezone.now()
    return CmsRoleAssignment.objects.filter(
        user_id=user_id, role=role, is_active=True, starts_at__lte=at, ends_at__gt=at
    ).exists()
