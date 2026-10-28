"""Read-only public ELM contract for other modules; plural signatures only."""

from collections.abc import Sequence

from modules.elm.models import LeaveRequest


def get_leave_requests(request_ids: Sequence[int]):
    """Return a mapping of request id to a small read-only projection."""
    ids = list({int(value) for value in request_ids})
    return {
        row.id: {
            "id": row.id,
            "user_id": row.user_id,
            "category": row.category,
            "status": row.status,
            "start_date": row.start_date,
            "end_date": row.end_date,
            "chargeable_days": row.chargeable_days,
        }
        for row in LeaveRequest.objects.filter(id__in=ids)
    }
