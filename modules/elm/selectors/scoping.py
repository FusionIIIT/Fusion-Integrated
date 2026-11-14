"""Who sees which rows. Out of scope is absent (404), never forbidden (403)."""
from __future__ import annotations

from django.db.models import Q, QuerySet

from modules.elm.domain import permissions as p
from modules.elm.domain import state_machine as sm
from modules.elm.models import LeaveRequest, Notification


def _uid(actor) -> int | None:
    return getattr(actor, "user_id", None)


def _has(actor, *codes: str) -> bool:
    check = getattr(actor, "has_permission", None)
    return bool(check) and any(check(c) for c in codes)


def own_requests(actor) -> QuerySet[LeaveRequest]:
    uid = _uid(actor)
    if uid is None or not _has(actor, p.P_VIEW):
        return LeaveRequest.objects.none()
    return LeaveRequest.objects.filter(user_id=uid)


def decision_queue(actor) -> QuerySet[LeaveRequest]:
    """Requests at the acting role's step; one's own only for Director self-sanction."""
    uid, role = _uid(actor), getattr(actor, "active_role", None)
    if uid is None or not role or not _has(actor, p.P_REVIEW, p.P_APPROVE):
        return LeaveRequest.objects.none()
    return (LeaveRequest.objects
            .filter(current_role=role,
                    status__in=(sm.PENDING - {sm.AWAITING_SUBSTITUTE,
                                              sm.SUBSTITUTE_DECLINED})
                    | {sm.CANCELLATION_PENDING})
            .exclude(Q(user_id=uid) & ~Q(route__0__step="director")))


def resumption_queue(actor) -> QuerySet[LeaveRequest]:
    uid, role = _uid(actor), getattr(actor, "active_role", None)
    if uid is None or not role or not _has(actor, p.P_RESUMPTION):
        return LeaveRequest.objects.none()
    return (LeaveRequest.objects
            .filter(current_role=role, status=sm.RESUMPTION_PENDING)
            .exclude(user_id=uid))


def substitution_requests(actor) -> QuerySet[LeaveRequest]:
    uid = _uid(actor)
    if uid is None or not _has(actor, p.P_SUBSTITUTE):
        return LeaveRequest.objects.none()
    return LeaveRequest.objects.filter(substitute_user_id=uid).exclude(user_id=uid)


def visible_requests(actor) -> QuerySet[LeaveRequest]:
    """Detail reads: one's own, one's substitution asks, and one's queues."""
    return (own_requests(actor) | substitution_requests(actor)
            | decision_queue(actor) | resumption_queue(actor)).distinct()


def notifications_for(actor) -> QuerySet[Notification]:
    uid, role = _uid(actor), getattr(actor, "active_role", None)
    if uid is None:
        return Notification.objects.none()
    q = Q(recipient_user_id=uid)
    if role:
        q |= Q(recipient_role=role, recipient_user_id__isnull=True)
    return Notification.objects.filter(q)
