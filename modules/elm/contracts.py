"""Public ELM contract for other Fusion modules.

`get_on_leave` returns the subset of supplied IAM user IDs who have an approved
leave interval covering the requested date. Other modules must not import ELM
models or services directly.
"""
from collections.abc import Sequence
from datetime import date

from django.db.models import Q

from modules.elm.models import LeaveRequest


def get_on_leave(user_ids: Sequence[int], on: date) -> set[int]:
    ids = {int(user_id) for user_id in user_ids if user_id is not None}
    if not ids:
        return set()
    return set(LeaveRequest.objects.filter(
        Q(status__in=("approved", "resumption_pending"))
        | Q(status__in=("resumption_reviewed_no_adjustment", "resumption_reviewed_early", "resumption_reviewed_late"), actual_return_date__gte=on),
        user_id__in=ids,
        start_date__lte=on,
        end_date__gte=on,
        kind__in=("leave", "extension"),
    ).values_list("user_id", flat=True))

