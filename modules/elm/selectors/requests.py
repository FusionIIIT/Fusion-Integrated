from django.db.models import Q

from modules.elm.models import LeaveRequest, WorkflowTask


def requests_for(actor):
    """Scope rows by owner or an explicitly assigned workflow task.

    A review permission is not global visibility. `view_all` is a separate,
    deliberately privileged grant; otherwise a foreign request is absent (404).
    """
    if actor is None:
        return LeaveRequest.objects.none()
    roles = list(getattr(actor, "roles", ()))
    visible_tasks = (
        WorkflowTask.objects.filter(status="open")
        .filter(Q(assigned_user_id=actor.user_id) | Q(assigned_role__in=roles))
        .values("request_id")
    )
    return LeaveRequest.objects.filter(
        Q(user_id=actor.user_id)
        | Q(current_approver_user_id=actor.user_id)
        | Q(pk__in=visible_tasks)
    ).distinct()


def tasks_for(actor):
    if actor is None:
        return WorkflowTask.objects.none()
    return WorkflowTask.objects.filter(status="open").filter(
        Q(assigned_user_id=actor.user_id) | Q(assigned_role__in=list(getattr(actor, "roles", ())))
    )
