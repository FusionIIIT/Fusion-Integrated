"""Read layer and scoping queries for Employee Leave Management.

All reads go through here so ownership and scope are resolved in one place,
and unauthorized access to another user's application naturally results in 404.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from core.api.exceptions import NotFoundError
from modules.elm.models import LeaveApplication

if TYPE_CHECKING:
    from django.db.models import QuerySet


def visible_leave_applications(
    principal,
    *,
    status: str | None = None,
    category: str | None = None,
) -> QuerySet[LeaveApplication]:
    """Return all leave applications visible to the given principal."""
    if principal is not None and principal.has_permission("elm.leave_application.manage"):
        qs = LeaveApplication.objects.all()
    elif principal is not None:
        qs = LeaveApplication.objects.filter(user_id=principal.user_id)
    else:
        qs = LeaveApplication.objects.none()

    if status:
        qs = qs.filter(status=status)
    if category:
        qs = qs.filter(category=category)

    return qs


def get_leave_application(principal, application_id: int) -> LeaveApplication:
    """Retrieve a single leave application within caller's scope, or raise NotFoundError."""
    qs = visible_leave_applications(principal)
    try:
        return qs.get(pk=application_id)
    except LeaveApplication.DoesNotExist as exc:
        raise NotFoundError(f"Leave application {application_id} not found.") from exc
