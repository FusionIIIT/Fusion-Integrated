"""Cross-module contracts exposed by ELM."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from modules.elm.domain import state_machine as sm
from modules.elm.models import LeaveRequest


def get_on_leave(user_ids: Sequence[int], on: date) -> set[int]:
    """Return user_ids from `user_ids` who have approved leave covering `on`."""
    if not user_ids:
        return set()
    return set(
        LeaveRequest.objects.filter(
            user_id__in=list(user_ids),
            status__in=[sm.APPROVED, sm.CANCELLATION_PENDING, sm.RESUMPTION_PENDING],
            start_date__lte=on,
            end_date__gte=on,
        ).values_list("user_id", flat=True)
    )
