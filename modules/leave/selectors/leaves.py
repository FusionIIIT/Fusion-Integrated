"""Role scope for leave. Narrow first, so foreign id is 404."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.leave.models import LeaveRequest

P_VIEW_ALL = "elm.leave.view"
P_RECOMMEND = "elm.leave.recommend"
P_DECIDE = "elm.leave.decide"

STAFF_PERMS = (P_VIEW_ALL, P_RECOMMEND, P_DECIDE,
               "elm.leave.verify", "elm.leave.report")


def _own_id(actor) -> int | None:
    return getattr(actor, "user_id", None)


def _has(actor, *codes: str) -> bool:
    check = getattr(actor, "has_permission", None)
    return bool(check) and any(check(c) for c in codes)


def is_staff(actor) -> bool:
    return _has(actor, *STAFF_PERMS)


def leaves_for(actor) -> QuerySet[LeaveRequest]:
    base = LeaveRequest.objects.all().order_by("-created_at")
    if actor is None:
        return base  # local viewing only, no IAM principal
    if is_staff(actor):
        return base
    own = _own_id(actor)
    return base.filter(user_id=own) if own is not None else base.none()
