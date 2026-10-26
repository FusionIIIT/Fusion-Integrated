"""All reads. Ownership filtering lives here (README convention) — a
not-owned id is simply absent, which is why detail access 404s, not 403s."""
from __future__ import annotations

from django.db.models import Q, QuerySet

from modules.elm.models import LeaveRequest, Status


def for_applicant(user_id: int) -> QuerySet[LeaveRequest]:
    return LeaveRequest.objects.filter(applicant_user_id=user_id)


def for_unit_head(user_id: int) -> QuerySet[LeaveRequest]:
    return LeaveRequest.objects.filter(unit_head_user_id=user_id)


def visible_to(user_id: int) -> QuerySet[LeaveRequest]:
    """Everything the principal may see: their own requests, plus anything
    routed to them for a Unit Head decision."""
    return LeaveRequest.objects.filter(
        Q(applicant_user_id=user_id) | Q(unit_head_user_id=user_id)
    )


def active_for_applicant(user_id: int) -> QuerySet[LeaveRequest]:
    """BR-EL-012 overlap check pool: pending + not-yet-superseded approved."""
    return for_applicant(user_id).filter(
        status__in=[
            Status.PENDING,
            Status.UNIT_HEAD_RECOMMENDED,
            Status.APPROVED,
        ]
    )


def active_for_substitute(user_id: int) -> QuerySet[LeaveRequest]:
    """BR-EL-014 conflict check pool: the candidate's own active leave."""
    return LeaveRequest.objects.filter(
        substitute_user_id=user_id,
        status__in=[Status.PENDING, Status.UNIT_HEAD_RECOMMENDED, Status.APPROVED],
    ) | active_for_applicant(user_id)
