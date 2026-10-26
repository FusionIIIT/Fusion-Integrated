"""Read-only selectors for leave requests."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.elm.domain.entities import LeaveStatus
from modules.elm.models.leaves import LeaveRequest


def visible_leaves_for_user(user_id: int) -> QuerySet[LeaveRequest]:
    """Retrieve all leave applications submitted by a user, newest first."""
    return (
        LeaveRequest.objects.filter(user_id=user_id)
        .prefetch_related("transitions")
        .order_by("-created_at")
    )


def pending_substitute_requests(substitute_user_id: int) -> QuerySet[LeaveRequest]:
    """Retrieve all leave requests awaiting this substitute's response."""
    return (
        LeaveRequest.objects.filter(
            substitute_user_id=substitute_user_id,
            status=LeaveStatus.AWAITING_SUBSTITUTE.value,
        )
        .order_by("-created_at")
    )


def pending_unit_head_reviews(unit_head_user_id: int | None = None) -> QuerySet[LeaveRequest]:
    """Retrieve all leave applications awaiting Unit Head review."""
    qs = LeaveRequest.objects.filter(status=LeaveStatus.AWAITING_UNIT_HEAD.value)
    if unit_head_user_id is not None:
        qs = qs.filter(unit_head_user_id=unit_head_user_id)
    return qs.order_by("-created_at")


def pending_sanctions(authority_user_id: int | None = None) -> QuerySet[LeaveRequest]:
    """Retrieve all leave applications awaiting Sanctioning Authority decision."""
    qs = LeaveRequest.objects.filter(status=LeaveStatus.AWAITING_SANCTION.value)
    if authority_user_id is not None:
        qs = qs.filter(sanctioning_authority_user_id=authority_user_id)
    return qs.order_by("-created_at")


def get_leave_by_id(leave_id: int) -> LeaveRequest | None:
    """Retrieve a single leave request by primary key."""
    try:
        return (
            LeaveRequest.objects.prefetch_related("transitions")
            .get(pk=leave_id)
        )
    except LeaveRequest.DoesNotExist:
        return None
