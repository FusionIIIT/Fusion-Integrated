"""Who sees which rows. Out-of-scope rows are absent, so detail views 404."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.elm.domain import state_machine as sm
from modules.elm.models import ApprovalStep, LeaveRequest, Notification


def _with_chain(qs: QuerySet[LeaveRequest]) -> QuerySet[LeaveRequest]:
    return qs.prefetch_related("steps")


def own_requests(principal) -> QuerySet[LeaveRequest]:
    """EL-UC-012: an employee sees only their own requests."""
    if principal is None or not principal.has_permission(sm.P_CREATE):
        return LeaveRequest.objects.none()
    return _with_chain(LeaveRequest.objects.filter(user_id=principal.user_id))


def _assigned(principal, stages) -> QuerySet[LeaveRequest]:
    steps = ApprovalStep.objects.filter(assignee_id=principal.user_id,
                                        status=ApprovalStep.ACTIVE,
                                        stage__in=list(stages))
    return LeaveRequest.objects.filter(id__in=steps.values("request_id"))


def substitute_tasks(principal) -> QuerySet[LeaveRequest]:
    """EL-UC-002: the active step names this employee as substitute."""
    if principal is None or not principal.has_permission(sm.P_CREATE):
        return LeaveRequest.objects.none()
    return _with_chain(_assigned(principal, [sm.SUBSTITUTE]))


def review_tasks(principal) -> QuerySet[LeaveRequest]:
    """Active steps assigned to this person, at stages the acting role may decide."""
    if principal is None:
        return LeaveRequest.objects.none()
    stages = [stage for stage, perm in sm.STAGE_PERMISSION.items()
              if stage != sm.SUBSTITUTE and principal.has_permission(perm)]
    if not stages:
        return LeaveRequest.objects.none()
    qs = _assigned(principal, stages)
    # Nobody reviews their own leave, except the Director's self-sanction.
    own = ApprovalStep.objects.filter(request__user_id=principal.user_id,
                                      status=ApprovalStep.ACTIVE).exclude(
        stage=sm.DIRECTOR)
    return _with_chain(qs.exclude(id__in=own.values("request_id")))


def visible_requests(principal) -> QuerySet[LeaveRequest]:
    """Union of the three, for detail lookups."""
    if principal is None:
        return LeaveRequest.objects.none()
    ids = (own_requests(principal).values("id")
           .union(substitute_tasks(principal).values("id"),
                  review_tasks(principal).values("id")))
    return _with_chain(LeaveRequest.objects.filter(id__in=ids))


def own_notifications(principal) -> QuerySet[Notification]:
    if principal is None:
        return Notification.objects.none()
    return Notification.objects.filter(user_id=principal.user_id)
