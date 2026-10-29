"""Who may see which leave rows, decided in one place (BR-EL-036).

Every list and detail view starts from a queryset built here, so a row the
caller may not see is a 404 rather than a 403 — a 403 would confirm it exists,
which for a leave record is itself a disclosure.

Scope is a narrowing of rows, never a permission: the same `leave.request.approve`
lets a Unit Head decide their own department's leave and a Director decide any,
and the difference lives here.
"""
from __future__ import annotations

from django.db.models import Q, QuerySet

from modules.leave.models import (
    ApprovalTask,
    CancellationRequest,
    ExtensionRequest,
    HierarchyRouteStep,
    LeaveRequest,
    OrganizationalUnit,
    ResumptionRequest,
)
from modules.leave.models.requests import TASK_PENDING

P_VIEW = "leave.request.view"
P_APPROVE = "leave.request.approve"
P_RECORDS = "leave.record.maintain"
P_BALANCE = "leave.balance.update"


def _has(actor, *codes: str) -> bool:
    check = getattr(actor, "has_permission", None)
    return bool(check) and any(check(c) for c in codes)


def _own_id(actor) -> int | None:
    """No identity to scope by resolves to an empty queryset, never to all."""
    return getattr(actor, "user_id", None)


def units_headed_by(actor) -> QuerySet[OrganizationalUnit]:
    own = _own_id(actor)
    if own is None:
        return OrganizationalUnit.objects.none()
    return OrganizationalUnit.objects.filter(head_user_id=own, is_active=True)


def _is_unit_head(actor) -> bool:
    own = _own_id(actor)
    return own is not None and OrganizationalUnit.objects.filter(
        head_user_id=own, is_active=True).exists()


def _is_configured_authority(actor) -> bool:
    """A person an administrator put into a routing step."""
    own = _own_id(actor)
    if own is None:
        return False
    return HierarchyRouteStep.objects.filter(user_id=own).exists()


def _is_leave_administrator(actor) -> bool:
    return _has(actor, P_RECORDS)


def requests_for(actor) -> QuerySet[LeaveRequest]:
    """The leave rows this actor may open."""
    base = LeaveRequest.objects.select_related("org_unit")
    own = _own_id(actor)

    # BR-EL-037: record maintenance is not sanctioning, so it is the widest
    # read scope and is the only one that is not also a decision scope.
    if _is_leave_administrator(actor):
        return base

    if own is None:
        return base.none()

    visible = Q(user_id=own)
    if _is_unit_head(actor):
        visible |= Q(org_unit__in=units_headed_by(actor))
    if _is_configured_authority(actor) or _has(actor, P_APPROVE):
        visible |= Q(tasks__assignee_user_id=own)
    return base.filter(visible).distinct()


def may_read_request(actor, request: LeaveRequest) -> bool:
    return requests_for(actor).filter(pk=request.pk).exists()


def tasks_for(actor) -> QuerySet[ApprovalTask]:
    """Open tasks addressed to this actor, which is their decision queue."""
    own = _own_id(actor)
    if own is None:
        return ApprovalTask.objects.none()
    return (ApprovalTask.objects
            .filter(assignee_user_id=own, status=TASK_PENDING)
            .select_related("leave_request"))


def cancellations_for(actor) -> QuerySet[CancellationRequest]:
    return CancellationRequest.objects.filter(
        leave_request__in=requests_for(actor)).select_related("leave_request")


def extensions_for(actor) -> QuerySet[ExtensionRequest]:
    return ExtensionRequest.objects.filter(
        leave_request__in=requests_for(actor)).select_related("leave_request")


def resumptions_for(actor) -> QuerySet[ResumptionRequest]:
    return ResumptionRequest.objects.filter(
        leave_request__in=requests_for(actor)).select_related("leave_request")


def balances_for(actor) -> QuerySet:
    """BR-EL-026: a Leave Administrator may read any account; everyone else only
    their own. The employee-facing balance screen is EL-UC-012."""
    from modules.leave.models import LeaveBalance

    base = LeaveBalance.objects.all()
    if _is_leave_administrator(actor):
        return base
    own = _own_id(actor)
    return base.filter(user_id=own) if own is not None else base.none()