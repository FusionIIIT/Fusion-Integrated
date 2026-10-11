from modules.leave.models import LeaveRequest


def visible_requests(principal):
    """Keep employee ownership filtering in one place."""
    if principal.has_permission("leave.request.view") or principal.has_permission(
            "leave.request.review"):
        return LeaveRequest.objects.select_related("leave_type")
    return LeaveRequest.objects.filter(user_id=principal.user_id).select_related("leave_type")
