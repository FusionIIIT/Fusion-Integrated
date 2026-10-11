"""Row visibility, decided in one place (BR-08, BR-11, BR-18).

Ownership is enforced by narrowing a queryset, never by fetching a row and then
checking it — so a row you may not see is a 404, not a 403. A 403 would confirm
it exists.
"""
from __future__ import annotations

from django.db.models import QuerySet

from modules.elm.models import LeaveApplication, LeaveBalanceEntry

#: Holding this widens what you see; scoping is why it is not a permission gate.
P_APPROVE = "elm.application.approve"


def _own_id(actor) -> int | None:
    """None means there is no identity to scope by — which resolves to nothing."""
    return getattr(actor, "user_id", None)


def is_approver(actor) -> bool:
    check = getattr(actor, "has_permission", None)
    return bool(check) and check(P_APPROVE)


def can_see(actor, application: LeaveApplication) -> bool:
    """One request. Approvers see everything; everyone else sees their own."""
    return is_approver(actor) or application.user_id == _own_id(actor)


def applications_for(actor) -> QuerySet[LeaveApplication]:
    base = LeaveApplication.objects.select_related("leave_type")
    if is_approver(actor):
        return base
    own = _own_id(actor)
    return base.filter(user_id=own) if own is not None else base.none()


def approvals_inbox(actor) -> QuerySet[LeaveApplication]:
    """Pending requests, never the caller's own (BR-08)."""
    base = (LeaveApplication.objects
            .select_related("leave_type")
            .filter(status="pending"))
    own = _own_id(actor)
    return base.exclude(user_id=own) if own is not None else base


def balance_entries_for(actor) -> QuerySet[LeaveBalanceEntry]:
    """The ledger rows a caller may read; the API aggregates them per type."""
    base = LeaveBalanceEntry.objects.select_related("leave_type")
    if is_approver(actor):
        return base
    own = _own_id(actor)
    return base.filter(user_id=own) if own is not None else base.none()
