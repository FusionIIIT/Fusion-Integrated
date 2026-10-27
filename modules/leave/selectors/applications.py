"""Read queries for leave applications."""
from __future__ import annotations

import datetime
from django.db.models import Q, QuerySet

from core.api.exceptions import NotFoundError
from modules.leave.models import LeaveApplication


def get_my_applications(user_id: int) -> QuerySet[LeaveApplication]:
    """Return all applications belonging to the user."""
    return LeaveApplication.objects.filter(user_id=user_id).order_by("-created_at")


def get_application_by_id(
    application_id: int,
    user_id: int | None = None,
    *,
    for_update: bool = False,
) -> LeaveApplication:
    """Fetch an application, optionally enforcing ownership and locking its row.

    Write services use ``for_update=True`` inside ``transaction.atomic`` so two
    reviewers cannot both act on the same pending workflow state.
    """
    try:
        queryset = LeaveApplication.objects.select_for_update() if for_update else LeaveApplication.objects.all()
        if user_id is not None:
            return queryset.get(pk=application_id, user_id=user_id)
        return queryset.get(pk=application_id)
    except LeaveApplication.DoesNotExist:
        raise NotFoundError(f"Leave application #{application_id} not found.", code="application_not_found")


def get_active_overlapping_leaves(
    user_id: int,
    start_date: datetime.date,
    end_date: datetime.date,
    exclude_id: int | None = None,
) -> QuerySet[LeaveApplication]:
    """Find active pending or approved leaves that overlap the date interval (BR-EL-012)."""
    active_statuses = {"substitute_pending", "under_review", "approved", "extension_requested"}
    qs = LeaveApplication.objects.filter(
        user_id=user_id,
        status__in=active_statuses,
        start_date__lte=end_date,
        end_date__gte=start_date,
    )
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    return qs
