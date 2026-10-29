from __future__ import annotations

from django.db.models import Q, QuerySet

from modules.directory import contracts as directory
from modules.leave.models import LeaveRequest

P_ADMIN = "leave.admin.manage"
P_VIEW = "leave.request.view"


def _own_id(actor) -> int | None:
    return getattr(actor, "user_id", None)


def _has(actor, *codes: str) -> bool:
    check = getattr(actor, "has_permission", None)
    return bool(check) and any(check(c) for c in codes)


def _department_user_ids(own: int) -> list[int]:
    me = directory.get_users([own]).get(own)
    if me is None or not me.department:
        return []
    return [e.user_id for e in directory.get_employees() if e.department == me.department]


def requests_for(actor) -> QuerySet[LeaveRequest]:
    base = LeaveRequest.objects.all()
    own = _own_id(actor)

    if own is None:
        return base.none()

    if _has(actor, P_ADMIN):
        return base

    scope = Q(user_id=own) | Q(current_assignee_id=own)

    if _has(actor, P_VIEW):
        scope |= Q(user_id__in=_department_user_ids(own))

    return base.filter(scope)