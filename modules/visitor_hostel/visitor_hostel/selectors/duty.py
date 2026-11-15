"""Who is on duty right now."""
from __future__ import annotations

from django.utils import timezone

from modules.visitor_hostel.models import DutyAssignment


def current(role: str, now=None) -> DutyAssignment | None:
    """The open, in-window assignment for a role, or None. An assignment past
    its end counts as nobody, even before the sweep closes it (BR-VH-047)."""
    now = now or timezone.now()
    return (DutyAssignment.objects
            .filter(role=role, ended_at__isnull=True, valid_from__lte=now,
                    valid_until__gt=now)
            .first())


def current_holder_id(role: str, now=None) -> int | None:
    row = current(role, now)
    return row.user_id if row else None
