"""Who may see which rows, decided once.

Every list and detail read starts here and ownership is enforced by narrowing a
queryset, never by fetching a row and then checking it, so a row outside your
scope is absent and therefore 404 (BR-EL-036).
"""
from __future__ import annotations

from django.db.models import Q, QuerySet

from modules.leave.models import (
    LeaveAccount,
    LeaveRequest,
    ResumptionSubmission,
    SubstituteAssignment,
)

P_VIEW = "leave.request.view"
P_REVIEW = "leave.request.review"
P_APPROVE = "leave.request.approve"
P_RECORDS = "leave.record.view"
P_BALANCE = "leave.balance.view"

#: Any of these opens the module's office scope.
OFFICE_PERMISSIONS = (P_VIEW, P_RECORDS, P_REVIEW, P_APPROVE)


def _has(actor, *codes: str) -> bool:
    check = getattr(actor, "has_permission", None)
    return bool(check) and any(check(c) for c in codes)


def designations(actor) -> set[str]:
    """The ACTING role only, plus the designations it holds.

    A person acting as one role must not see another role's queue, so the
    acting role leads and the fallback set is only used when it is empty.
    """
    active = getattr(actor, "active_role", None)
    roles = set(getattr(actor, "roles", ()) or ())
    if active:
        roles.add(active)
    return {r for r in roles if r}


def sees_everything(actor) -> bool:
    return _has(actor, P_RECORDS)


def is_office(actor) -> bool:
    return _has(actor, *OFFICE_PERMISSIONS)


def own_id(actor) -> int | None:
    return getattr(actor, "user_id", None)


def requests_for(actor) -> QuerySet[LeaveRequest]:
    """Requests this actor may read: their own, their queue, or everything."""
    qs = LeaveRequest.objects.select_related("parent")
    me = own_id(actor)
    if sees_everything(actor):
        return qs
    if _has(actor, P_REVIEW, P_APPROVE):
        mine = designations(actor)
        return qs.filter(Q(current_step_designation__in=mine) | Q(user_id=me))
    return qs.filter(user_id=me)


def request_for(actor, request_id: int) -> LeaveRequest | None:
    return requests_for(actor).filter(pk=request_id).first()


def my_requests(actor) -> QuerySet[LeaveRequest]:
    return LeaveRequest.objects.filter(user_id=own_id(actor))


def substitutes_for(actor) -> QuerySet[SubstituteAssignment]:
    """Assignments this actor was nominated for, newest first."""
    return (SubstituteAssignment.objects
            .filter(substitute_user_id=own_id(actor))
            .select_related("request"))


def resumptions_for(actor) -> QuerySet[ResumptionSubmission]:
    if _has(actor, P_RECORDS):
        return ResumptionSubmission.objects.select_related("request")
    if _has(actor, P_REVIEW, P_APPROVE):
        return ResumptionSubmission.objects.filter(
            request__current_step_designation__in=designations(actor))
    return ResumptionSubmission.objects.filter(
        request__user_id=own_id(actor))


def accounts_for(actor, *, user_id: int | None = None) -> QuerySet[LeaveAccount]:
    """Own accounts by default; the office scope is what widens it."""
    if sees_everything(actor) or _has(actor, P_VIEW):
        if user_id is None:
            return LeaveAccount.objects.all()
        return LeaveAccount.objects.filter(user_id=user_id)
    return LeaveAccount.objects.filter(user_id=own_id(actor))
