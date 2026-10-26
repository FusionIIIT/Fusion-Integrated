from __future__ import annotations

from django.db.models import Q, QuerySet

from modules.leave.models import LeaveBalance, LeaveRequest, Resumption


def requests_for(actor) -> QuerySet[LeaveRequest]:
    """Requests the actor may see, decided in one place (BR-EL-036)."""
    if not hasattr(actor, "user_id"):
        return LeaveRequest.objects.none()

    if actor.has_permission("leave.offline.record"):
        return LeaveRequest.objects.select_related("unit")

    own_id = actor.user_id
    q = Q(user_id=own_id) | Q(substitute_user_id=own_id)

    if actor.has_permission("leave.request.review"):
        q |= Q(unit__unit_head_user_id=own_id)
    if actor.has_permission("leave.request.route"):
        q |= Q(status="routing")
    if actor.has_permission("leave.request.sanction"):
        q |= Q(status="sanction")

    return LeaveRequest.objects.filter(q).select_related("unit")


def resumptions_for(actor) -> QuerySet[Resumption]:
    """Resumptions the actor may see (EL-UC-011, BR-EL-027, BR-EL-036)."""
    if not hasattr(actor, "user_id"):
        return Resumption.objects.none()

    if actor.has_permission("leave.offline.record"):
        return Resumption.objects.select_related("request")

    own_id = actor.user_id
    q = Q(request__user_id=own_id)
    if actor.has_permission("leave.resumption.verify"):
        q |= Q(request__unit__unit_head_user_id=own_id)

    return Resumption.objects.filter(q).select_related("request")


def balances_for(actor) -> QuerySet[LeaveBalance]:
    """The actor's own leave balances (EL-UC-012, BR-EL-036)."""
    if not hasattr(actor, "user_id"):
        return LeaveBalance.objects.none()

    own_id = actor.user_id

    if actor.has_permission("leave.balance.view"):
        return LeaveBalance.objects.filter(user_id=own_id)

    return LeaveBalance.objects.none()
