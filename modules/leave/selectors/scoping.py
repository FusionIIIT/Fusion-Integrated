from __future__ import annotations

from django.db.models import Q, QuerySet

from modules.leave.models import LeaveBalance, LeaveRequest


def requests_for(actor) -> QuerySet[LeaveRequest]:
    """EL-UC-001/007/008/010, BR-EL-011, BR-EL-012, BR-EL-015, BR-EL-016, BR-EL-017, BR-EL-018, BR-EL-019, BR-EL-020, BR-EL-021, BR-EL-022, BR-EL-023, BR-EL-024, BR-EL-025, BR-EL-027, BR-EL-028, BR-EL-029, BR-EL-030, BR-EL-031, BR-EL-032, BR-EL-033, BR-EL-034, BR-EL-035, BR-EL-036, BR-EL-037, BR-EL-038

    Returns a queryset of LeaveRequests for the given actor based on their role and permissions.
    """
    if not hasattr(actor, "user_id"):
        return LeaveRequest.objects.none()

    own_id = actor.user_id

    if actor.has_permission("leave.request.create"):
        return LeaveRequest.objects.filter(
            Q(unit__unit_head_user_id=own_id)
            | Q(substitute_user_id=own_id)
            | Q(status="routing")
            | Q(status="sanction")
        )

    return LeaveRequest.objects.none()


def resumptions_for(actor) -> QuerySet[LeaveRequest]:
    """EL-UC-011, BR-EL-011, BR-EL-012, BR-EL-015, BR-EL-016, BR-EL-017, BR-EL-018, BR-EL-019, BR-EL-020, BR-EL-021, BR-EL-022, BR-EL-023, BR-EL-024, BR-EL-025, BR-EL-027, BR-EL-028, BR-EL-029, BR-EL-030, BR-EL-031, BR-EL-032, BR-EL-033, BR-EL-034, BR-EL-035, BR-EL-036, BR-EL-037, BR-EL-038

    Returns a queryset of LeaveRequests for resumption review for the given actor based on their role and permissions.
    """
    if not hasattr(actor, "user_id"):
        return LeaveRequest.objects.none()

    own_id = actor.user_id

    if actor.has_permission("leave.resumption.verify"):
        return LeaveRequest.objects.filter(Q(status="routing") | Q(status="sanction"))

    return LeaveRequest.objects.none()


def balances_for(actor) -> QuerySet[LeaveBalance]:
    """EL-UC-012, BR-EL-011, BR-EL-012, BR-EL-015, BR-EL-016, BR-EL-017, BR-EL-018, BR-EL-019, BR-EL-020, BR-EL-021, BR-EL-022, BR-EL-023, BR-EL-024, BR-EL-025, BR-EL-027, BR-EL-028, BR-EL-029, BR-EL-030, BR-EL-031, BR-EL-032, BR-EL-033, BR-EL-034, BR-EL-035, BR-EL-036, BR-EL-037, BR-EL-038

    Returns a queryset of LeaveBalances for the given actor based on their role and permissions.
    """
    if not hasattr(actor, "user_id"):
        return LeaveBalance.objects.none()

    own_id = actor.user_id

    if actor.has_permission("leave.balance.view"):
        return LeaveBalance.objects.filter(user_id=own_id)

    return LeaveBalance.objects.none()
