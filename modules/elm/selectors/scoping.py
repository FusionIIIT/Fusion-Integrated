"""Who sees which rows. Out-of-scope rows are absent, so detail views 404."""
from __future__ import annotations

from django.db.models import Q, QuerySet

from modules.elm.domain import state_machine as sm
from modules.elm.models import LeaveRequest, Notification


def own_requests(principal) -> QuerySet[LeaveRequest]:
    """EL-UC-012: an employee sees only their own requests."""
    if principal is None or not principal.has_permission(sm.P_CREATE):
        return LeaveRequest.objects.none()
    return LeaveRequest.objects.filter(user_id=principal.user_id)


def substitute_tasks(principal) -> QuerySet[LeaveRequest]:
    """EL-UC-002: requests naming this employee as substitute, awaiting reply."""
    if principal is None or not principal.has_permission(sm.P_CREATE):
        return LeaveRequest.objects.none()
    return LeaveRequest.objects.filter(substitute_id=principal.user_id,
                                       state=sm.AWAITING_SUBSTITUTE)


def review_tasks(principal) -> QuerySet[LeaveRequest]:
    """Tasks assigned to this person, at stages the acting role may decide."""
    if principal is None:
        return LeaveRequest.objects.none()
    states = [state for state, (_, perm) in sm.REVIEW_STAGE.items()
              if principal.has_permission(perm)]
    if not states:
        return LeaveRequest.objects.none()
    qs = LeaveRequest.objects.filter(assignee_id=principal.user_id,
                                     state__in=states)
    # Nobody reviews their own leave, except the Director's self-sanction.
    return qs.filter(~Q(user_id=principal.user_id)
                     | Q(state=sm.AWAITING_DIRECTOR))


def visible_requests(principal) -> QuerySet[LeaveRequest]:
    """Union of the three, for detail lookups."""
    if principal is None:
        return LeaveRequest.objects.none()
    ids = (own_requests(principal).values("id")
           .union(substitute_tasks(principal).values("id"),
                  review_tasks(principal).values("id")))
    return LeaveRequest.objects.filter(id__in=ids)


def own_notifications(principal) -> QuerySet[Notification]:
    if principal is None:
        return Notification.objects.none()
    return Notification.objects.filter(user_id=principal.user_id)
