"""Who sees which rows, decided once; a row outside scope is absent, so it is a 404 (BR-EL-036)."""
from __future__ import annotations

from django.db.models import Q, QuerySet

from modules.leave.domain import routing
from modules.leave.domain import state_machine as sm
from modules.leave.models import LeaveRequest, Substitution, Task

P_RECORDS = "leave.record.view"


def _uid(actor) -> int | None:
    return getattr(actor, "user_id", None)


def _role(actor) -> str:
    return (getattr(actor, "active_role", None) or "").strip()


def _has(actor, code: str) -> bool:
    check = getattr(actor, "has_permission", None)
    return bool(check) and check(code)


def own_requests(actor) -> QuerySet[LeaveRequest]:
    uid = _uid(actor)
    base = LeaveRequest.objects.select_related("parent")
    return base.filter(user_id=uid) if uid is not None else base.none()


def queue(actor) -> QuerySet[Task]:
    """Open tasks for the role being acted as; never the actor's own request, bar BR-EL-020."""
    uid, role = _uid(actor), _role(actor)
    if uid is None or not role:
        return Task.objects.none()
    mine = Q(assignee_designation=role) & ~Q(step=sm.DIRECTOR) & ~Q(request__user_id=uid)
    director_self = (Q(step=sm.DIRECTOR, request__user_id=uid)
                     if role == routing.DIRECTOR_DESIGNATION else Q(pk__in=[]))
    resumption_self = (Q(step="resumption_review", assignee_designation=role,
                         request__user_id=uid, request__is_director_applicant=True)
                       if role == routing.DIRECTOR_DESIGNATION else Q(pk__in=[]))
    return (Task.objects.filter(status=Task.OPEN)
            .filter(mine | director_self | resumption_self)
            .select_related("request", "request__parent", "request__resumption")
            .order_by("opened_at", "id"))


def substitution_requests(actor) -> QuerySet[Substitution]:
    uid = _uid(actor)
    if uid is None:
        return Substitution.objects.none()
    return (Substitution.objects.filter(substitute_user_id=uid, status=Substitution.PENDING,
                                        request__status=sm.AWAITING_SUBSTITUTE)
            .select_related("request").order_by("created_at", "id"))


def visible_requests(actor) -> QuerySet[LeaveRequest]:
    """Own, tasked to the acting role, or nominated to cover; everything for a records holder."""
    uid, role = _uid(actor), _role(actor)
    base = LeaveRequest.objects.select_related("parent")
    if uid is None:
        return base.none()
    if _has(actor, P_RECORDS):
        return base
    tasked = Task.objects.filter(assignee_designation=role).values("request_id") if role else []
    nominated = Substitution.objects.filter(substitute_user_id=uid).values("request_id")
    scope = Q(user_id=uid) | Q(pk__in=nominated)
    if role:
        scope |= Q(pk__in=tasked)
    return base.filter(scope)


def records_for(actor) -> QuerySet[LeaveRequest]:
    if not _has(actor, P_RECORDS):
        return LeaveRequest.objects.none()
    return LeaveRequest.objects.select_related("parent")
