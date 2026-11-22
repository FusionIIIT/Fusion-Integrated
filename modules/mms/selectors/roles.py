"""Active operational role lookups."""

from django.db.models import Q
from django.utils import timezone

from modules.mms.models import RoleAssignment


def is_active_holder(*, role: str, user_id: int) -> bool:
    now = timezone.now()
    return (
        RoleAssignment.objects.filter(role=role, user_id=user_id, starts_at__lte=now)
        .filter(
            Q(ends_at__isnull=True) | Q(ends_at__gt=now),
        )
        .exists()
    )
