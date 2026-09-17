"""What each role may see."""
from __future__ import annotations

from django.db.models import Q, QuerySet

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
    """Everything this person may open."""
    if principal.has_any_permission(*INSTITUTE_WIDE):
        return LeaveRequest.objects.all()
    if principal.has_any_permission("leave.request.review") and unit:
        return LeaveRequest.objects.filter(unit=unit) | mine(principal.user_id)
    return mine(principal.user_id)


def _queue(states, viewer_user_id: int) -> QuerySet[LeaveRequest]:
    """A work queue never contains the viewer's own request, bar one case."""
    mine_on_the_self_route = Q(
        user_id=viewer_user_id, state=State.AWAITING_SELF_SANCTION.value,
        self_sanction=True)
    return (
        LeaveRequest.objects.filter(state__in=states)
        # Your own leave, unless the route is the one made for it.
        .exclude(Q(user_id=viewer_user_id) & ~mine_on_the_self_route)
        # Somebody else's self-sanction belongs in nobody else's queue.
        .exclude(Q(self_sanction=True) & ~Q(user_id=viewer_user_id))
    )


def sees_whole_institute(principal) -> bool:
    """Whether this role acts on people from anywhere, or only their own unit."""
    return principal.has_any_permission(*INSTITUTE_WIDE)


def may_read_balance_of(principal, viewer_unit: str, subject_unit: str) -> bool:
    """BR-EL-019 scoping, applied to a figure rather than to a list."""
    if sees_whole_institute(principal):
        return True
    return bool(viewer_unit) and viewer_unit == subject_unit


def review_queue(unit: str, viewer_user_id: int) -> QuerySet[LeaveRequest]:
    """A unit head reviews their own unit, and not their own leave."""
    return _queue(REVIEW_STATES, viewer_user_id).filter(unit=unit)


def routing_queue(viewer_user_id: int) -> QuerySet[LeaveRequest]:
    return _queue(ROUTING_STATES, viewer_user_id)


def sanction_queue(viewer_user_id: int) -> QuerySet[LeaveRequest]:
    return _queue(SANCTION_STATES, viewer_user_id)


def resumption_queue(viewer_user_id: int) -> QuerySet[LeaveRequest]:
    return _queue(RESUMPTION_STATES, viewer_user_id)


def nominations_for(substitute_user_id: int) -> QuerySet[SubstituteNomination]:
    return SubstituteNomination.objects.filter(
        substitute_user_id=substitute_user_id,
        response=SubstituteNomination.Response.PENDING,
    ).select_related("request")
