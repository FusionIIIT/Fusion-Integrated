from modules.leave.models import LeaveManagerAssignment, LeaveRequest


def visible_requests(principal):
    """Return only the caller's requests or explicitly assigned reports."""
    base = LeaveRequest.objects.select_related("leave_type")
    if principal.has_permission("leave.request.view") or principal.has_permission(
            "leave.request.review"):
        employee_ids = LeaveManagerAssignment.objects.filter(
            manager_user_id=principal.user_id).values("employee_user_id")
        return base.filter(user_id__in=employee_ids).exclude(user_id=principal.user_id)
    return base.filter(user_id=principal.user_id)
