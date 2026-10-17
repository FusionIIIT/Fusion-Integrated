"""Reads. Ownership is decided here, once, so a view never touches
LeaveRequest.objects directly and a foreign id yields 404."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.elm.domain.entities import ACTIVE, HalfDay, LeaveSpan
from modules.elm.domain.state_machine import P_APPROVE, P_REVIEW, P_VIEW
from modules.elm.models import LeaveRequest


def is_reviewer(principal) -> bool:
    return principal.has_any_permission(P_VIEW, P_REVIEW, P_APPROVE)


def visible_requests(principal) -> QuerySet[LeaveRequest]:
    qs = LeaveRequest.objects.all()
    if is_reviewer(principal):
        return qs
    return qs.filter(applicant_user_id=principal.user_id)


def own_requests(principal) -> QuerySet[LeaveRequest]:
    return LeaveRequest.objects.filter(applicant_user_id=principal.user_id)


def active_spans(user_id: int) -> list[LeaveSpan]:
    """Every interval the employee already holds (BR-EL-012)."""
    rows = (LeaveRequest.objects
            .filter(applicant_user_id=user_id, status__in=[s.value for s in ACTIVE])
            .values_list("start_date", "end_date", "half"))
    return [LeaveSpan(s, e, HalfDay(h)) for s, e, h in rows]
