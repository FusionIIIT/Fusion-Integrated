"""Role scope for leave. Narrow first, so foreign id is 404."""
from __future__ import annotations

import datetime

from django.db.models import Q, QuerySet

from modules.leave.models import LeaveBalance, LeaveRequest

P_VIEW_ALL = "elm.leave.view"
P_RECOMMEND = "elm.leave.recommend"
P_DECIDE = "elm.leave.decide"

STAFF_PERMS = (
    P_VIEW_ALL,
    P_RECOMMEND,
    P_DECIDE,
    "elm.leave.verify",
    "elm.leave.report",
)


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
    if own is None:
        return base.none()
    return base.filter(Q(user_id=own) | Q(substitute_user_id=own))


def balances_for(user_id: int, year: int | None = None) -> QuerySet[LeaveBalance]:
    if year is None:
        year = datetime.date.today().year
    return LeaveBalance.objects.filter(user_id=user_id, year=year).order_by("category")
