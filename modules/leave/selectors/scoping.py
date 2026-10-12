"""Role scope, decided in one place.

Every list and detail view starts from a queryset built here. Ownership is
enforced by narrowing, never by fetching a row and then checking it — so a
row you may not see is a 404, not a 403. A 403 would confirm it exists.

Holding `leave.request.view` widens the list to every request; everyone else
sees their own plus the files where they hold a desk (their substitute turn,
their assigned task, their unit's review).
"""
from __future__ import annotations

from django.db.models import Q, QuerySet

from core.api.exceptions import NotFoundError
from modules.leave.domain import states as st
from modules.leave.models import LeaveBalance, LeaveNotification, LeaveRequest

P_VIEW_ALL = "leave.request.view"
P_VIEW_SELF = "leave.request.view_self"
P_VIEW_BALANCES = "leave.balance.view"


def _has(actor, *codes: str) -> bool:
    check = getattr(actor, "has_permission", None)
    return bool(check) and any(check(c) for c in codes)


def _own(actor) -> int | None:
    """None means no identity to scope by, which resolves to an empty
    queryset. Deny is the only safe reading of "who is asking?" being
    unanswerable."""
    return getattr(actor, "user_id", None)


def _involved(actor) -> Q:
    uid = _own(actor)
    return (Q(user_id=uid)
            | Q(substitute_user_id=uid)
            | Q(task_user_id=uid)
            | Q(unit_head_user_id=uid)
            | Q(establishment_user_id=uid)
            | Q(authority_user_id=uid)
            | Q(decided_by_user_id=uid))


def requests_for(actor) -> QuerySet[LeaveRequest]:
    qs = LeaveRequest.objects.all()
    if _has(actor, P_VIEW_ALL):
        return qs
    if _own(actor) is None:
        return qs.none()
    return qs.filter(_involved(actor)).distinct()


def request_or_404(actor, pk: int) -> LeaveRequest:
    row = requests_for(actor).filter(pk=pk).first()
    if row is None:
        raise NotFoundError("Leave request not found.", code="not_found")
    return row


def request_for_action(pk: int) -> LeaveRequest:
    """A row an actor wants to *act* on.

    Reads stay scoped (a stranger gets 404), but an action loads by id alone:
    the service's own identity gate then answers 403 "assigned to someone
    else", which is the honest answer when the file exists and is simply not
    yours — and never leaks anything a scoped read would not.
    """
    row = LeaveRequest.objects.filter(pk=pk).first()
    if row is None:
        raise NotFoundError("Leave request not found.", code="not_found")
    return row


def tasks_for(actor) -> QuerySet[LeaveRequest]:
    """Files waiting on *this* actor: their assigned task, their substitute
    turn, or their own action to take."""
    uid = _own(actor)
    if uid is None:
        return LeaveRequest.objects.none()
    return (LeaveRequest.objects
            .filter(status__in=st.PENDING)
            .filter(Q(task_user_id=uid)
                    | Q(substitute_user_id=uid,
                        status=st.AWAITING_SUBSTITUTE)
                    | Q(user_id=uid, status=st.APPLICANT_ACTION))
            .distinct())


def balances_rows_for(actor, user_id: int | None = None
                      ) -> QuerySet[LeaveBalance]:
    target = user_id if user_id is not None else _own(actor)
    if target is None:
        return LeaveBalance.objects.none()
    return LeaveBalance.objects.filter(user_id=target)


def notifications_for(actor) -> QuerySet[LeaveNotification]:
    uid = _own(actor)
    if uid is None:
        return LeaveNotification.objects.none()
    return LeaveNotification.objects.filter(user_id=uid)
