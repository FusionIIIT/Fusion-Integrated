from django.db.models import QuerySet

from modules.elm.models import LeaveRequest


def visible_to(actor) -> QuerySet[LeaveRequest]:
    base = LeaveRequest.objects.all()
    scopes = []
    if actor.has_permission("elm.leave_request.view_self"):
        scopes.append(base.filter(employee_user_id=actor.user_id))
    if actor.has_permission("elm.workflow.view") or actor.has_permission("elm.substitute.respond"):
        scopes.append(base.filter(assigned_user_id=actor.user_id))
    if actor.has_permission("elm.record.manage"):
        scopes.append(base)
    if not scopes:
        return base.none()
    result = scopes[0]
    for scope in scopes[1:]:
        result = result | scope
    return result.select_related("parent").distinct().order_by("-created_at")
