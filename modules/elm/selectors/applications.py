from datetime import date
from django.db.models import Q
from modules.elm.models import LeaveApplication


def visible_applications(principal):
    """Return applications visible to the principal."""
    qs = LeaveApplication.objects.all().prefetch_related("transitions")
    if principal.has_permission("leave_elm.application.view"):
        return qs
    return qs.filter(
        Q(user_id=principal.user_id) | Q(substitute_user_id=principal.user_id)
    )


def pending_substitute_requests(principal):
    """Return substitute requests waiting for the principal's consent."""
    return LeaveApplication.objects.filter(
        substitute_user_id=principal.user_id,
        substitute_status="pending",
        status="pending_substitute",
    )


def pending_approvals(principal):
    """Return applications waiting for Unit Head or higher sanction."""
    qs = LeaveApplication.objects.none()
    if principal.has_permission("leave_elm.application.review"):
        qs = qs | LeaveApplication.objects.filter(status="pending_unit_head")
    if principal.has_permission("leave_elm.application.approve"):
        qs = qs | LeaveApplication.objects.filter(
            status__in=["pending_unit_head", "pending_higher_sanction", "cancellation_requested"]
        )
    return qs.distinct()
