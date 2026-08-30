"""What each role may see.

Scope is a queryset, not a check after the fact: an employee's list is narrowed
to their own rows, so asking for somebody else's request returns nothing found
rather than a refusal that confirms it exists.
"""
from __future__ import annotations

from django.db.models import QuerySet

from modules.leave.domain.state_machine import State
from modules.leave.models import LeaveRequest, SubstituteNomination

REVIEW_STATES = (State.AWAITING_UNIT_HEAD.value, State.CANCELLATION_UNIT_HEAD.value,
                 State.EXTENSION_AWAITING_UNIT_HEAD.value)
ROUTING_STATES = (State.AWAITING_ESTABLISHMENT.value,
                  State.CANCELLATION_ESTABLISHMENT.value,
                  State.EXTENSION_AWAITING_ESTABLISHMENT.value)
SANCTION_STATES = (State.AWAITING_FINAL_SANCTION.value, State.AWAITING_SELF_SANCTION.value,
                   State.CANCELLATION_FINAL.value, State.EXTENSION_AWAITING_FINAL.value)
RESUMPTION_STATES = (State.AWAITING_RESUMPTION_VERIFICATION.value,)


def mine(user_id: int) -> QuerySet[LeaveRequest]:
    return LeaveRequest.objects.filter(user_id=user_id)


#: Roles that act on requests from anywhere in the institute.
INSTITUTE_WIDE = (
    "leave.request.route",
    "leave.request.sanction",
    "leave.resumption.verify",
    "leave.offline.record",
)


def visible_to(principal, unit: str = "") -> QuerySet[LeaveRequest]:
    """Everything this person may open.

    A unit head sees their own unit, not the institute. Holding
    `leave.balance.view` is not enough on its own: every unit head holds it, and
    reading it as institute-wide would let one department open another's leave
    records.
    """
    if principal.has_any_permission(*INSTITUTE_WIDE):
        return LeaveRequest.objects.all()
    if principal.has_any_permission("leave.request.review") and unit:
        return LeaveRequest.objects.filter(unit=unit) | mine(principal.user_id)
    return mine(principal.user_id)


def review_queue(unit: str) -> QuerySet[LeaveRequest]:
    """A unit head reviews their own unit and nobody else's.

    The unit is required rather than optional. An optional one defaults to
    "every unit" the moment a caller forgets it, and a widened queue is the
    kind of mistake that reads as working software.
    """
    return LeaveRequest.objects.filter(state__in=REVIEW_STATES, unit=unit)


def routing_queue() -> QuerySet[LeaveRequest]:
    return LeaveRequest.objects.filter(state__in=ROUTING_STATES)


def sanction_queue() -> QuerySet[LeaveRequest]:
    return LeaveRequest.objects.filter(state__in=SANCTION_STATES)


def resumption_queue() -> QuerySet[LeaveRequest]:
    return LeaveRequest.objects.filter(state__in=RESUMPTION_STATES)


def nominations_for(substitute_user_id: int) -> QuerySet[SubstituteNomination]:
    return SubstituteNomination.objects.filter(
        substitute_user_id=substitute_user_id,
        response=SubstituteNomination.Response.PENDING,
    ).select_related("request")
