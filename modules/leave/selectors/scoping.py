"""Whose rows each person sees. Out of scope is absent, so detail views 404."""
from __future__ import annotations

from django.db.models import Q, QuerySet

from modules.leave.domain.workflow import State
from modules.leave.models import LeaveRequest, Resumption

#: Holding this widens scope to every employee's records (EL-UC-017).
P_ALL_RECORDS = "leave_management.leave_record.update"


def _uid(actor) -> int | None:
    return getattr(actor, "user_id", None)


def requests_for(actor) -> QuerySet[LeaveRequest]:
    uid = _uid(actor)
    if uid is None:
        return LeaveRequest.objects.none()
    qs = LeaveRequest.objects.select_related("parent")
    if actor.has_permission(P_ALL_RECORDS):
        return qs
    return qs.filter(Q(user_id=uid) | Q(substitute_user_id=uid) | Q(unit_head_user_id=uid)
                     | Q(establishment_user_id=uid) | Q(sanctioning_user_id=uid))


def own_requests(actor) -> QuerySet[LeaveRequest]:
    uid = _uid(actor)
    if uid is None:
        return LeaveRequest.objects.none()
    return LeaveRequest.objects.select_related("parent").filter(user_id=uid)


def inbox_for(actor) -> QuerySet[LeaveRequest]:
    """Requests whose current step is this person's, and nobody else's."""
    uid = _uid(actor)
    if uid is None:
        return LeaveRequest.objects.none()
    return LeaveRequest.objects.select_related("parent").filter(
        Q(status=State.AWAITING_SUBSTITUTE, substitute_user_id=uid)
        | Q(status=State.AWAITING_UNIT_HEAD, unit_head_user_id=uid)
        | Q(status=State.AWAITING_ESTABLISHMENT, establishment_user_id=uid)
        | Q(status=State.AWAITING_FINAL, sanctioning_user_id=uid)
    ).exclude(user_id=uid).order_by("status_changed_at")


def resumptions_for_review(actor) -> QuerySet[Resumption]:
    uid = _uid(actor)
    if uid is None:
        return Resumption.objects.none()
    return (Resumption.objects.select_related("leave")
            .filter(status=Resumption.PENDING, reviewer_user_id=uid)
            .exclude(leave__user_id=uid))
