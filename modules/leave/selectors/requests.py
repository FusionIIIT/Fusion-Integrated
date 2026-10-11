"""Leave request selectors.

Encapsulates database queries for requests, overlap intervals, and substitute history.
"""
from datetime import date

from core.api.exceptions import NotFoundError
from fusion_auth.principal import Principal
from modules.leave.domain.constants import RequestStatus
from modules.leave.models.requests import LeaveRequest
from modules.leave.selectors.scoping import visible_requests_for_principal

TERMINAL_STATES = (
    RequestStatus.REJECTED.value,
    RequestStatus.WITHDRAWN.value,
    RequestStatus.CANCELLED.value,
    RequestStatus.EXTENSION_REJECTED.value,
    RequestStatus.EXTENSION_WITHDRAWN.value,
)


def get_request_by_id(request_id: int, principal: Principal) -> LeaveRequest:
    """Returns a leave request if visible to the principal; raises NotFoundError otherwise."""
    try:
        return visible_requests_for_principal(principal).get(id=request_id)
    except LeaveRequest.DoesNotExist:
        raise NotFoundError("Leave request not found.") from None


def get_active_intervals(
    user_id: int,
    exclude_request_id: int | None = None,
) -> list[tuple[date, date, str]]:
    """Returns active (pending or approved) intervals for overlap validation (BR-EL-012)."""
    qs = LeaveRequest.objects.filter(user_id=user_id).exclude(status__in=TERMINAL_STATES)
    if exclude_request_id:
        qs = qs.exclude(id=exclude_request_id)
    return [(r.start_date, r.end_date, r.half_day) for r in qs]


def get_substitute_active_intervals(
    substitute_user_id: int,
    exclude_request_id: int | None = None,
) -> list[tuple[date, date]]:
    """Returns active leave intervals for a nominated substitute (BR-EL-014)."""
    qs = LeaveRequest.objects.filter(user_id=substitute_user_id).exclude(status__in=TERMINAL_STATES)
    if exclude_request_id:
        qs = qs.exclude(id=exclude_request_id)
    return [(r.start_date, r.end_date) for r in qs]
