from django.db.models import Q, QuerySet

from core.api.exceptions import NotFoundError
from modules.leave.models import LeaveApplication, ReportingLine, Status


def my_applications(user_id: int) -> QuerySet:
    """Return a user's leave applications, newest first."""
    return (
        LeaveApplication.objects.prefetch_related("actions")
        .filter(user_id=user_id)
        .order_by("-created_at")
    )


def inbox(user_id: int) -> QuerySet:
    """Return pending leave applications assigned to a specific user (the assignee)."""
    return (
        LeaveApplication.objects.prefetch_related("actions")
        .filter(Q(assignee_id=user_id) & Q(status=Status.PENDING.value))
        .order_by("created_at")
    )


def visible_application(user_id: int, application_id: int) -> LeaveApplication:
    """
    Return a leave application if the user is the owner, the assignee, or the nominated substitute.
    Raises NotFoundError otherwise.
    """
    app = LeaveApplication.objects.prefetch_related("actions").filter(id=application_id).first()
    if app is None:
        raise NotFoundError()

    if user_id not in (app.user_id, app.assignee_id, app.substitute_id):
        raise NotFoundError(f"Access denied to application {application_id}")

    return app


def get_reporting_line(user_id: int) -> ReportingLine | None:
    """Return the reporting line for a user, or None if not configured."""
    try:
        return ReportingLine.objects.get(user_id=user_id)
    except ReportingLine.DoesNotExist:
        return None
