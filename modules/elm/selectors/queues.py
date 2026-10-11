"""Queue selectors — what is actionable for a person right now."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.elm.models import LeaveTask, SubstituteNomination


def queue_for(user_id: int) -> QuerySet[LeaveTask]:
    """Every pending task assigned to the caller, oldest first —
    the Unit Head review seat, the Establishment desk, the
    sanctioning authorities and substitute assignments all read
    from here."""
    return LeaveTask.objects.filter(
        assignee_user_id=user_id, status="pending").order_by("created_at")


def pending_tasks_for_request(request_id: int) -> QuerySet[LeaveTask]:
    return LeaveTask.objects.filter(request_id=request_id,
                                     status="pending")


def substitute_assignments(user_id: int) -> QuerySet[LeaveTask]:
    """Pending substitute (responsibility-holder) assignments."""
    return queue_for(user_id).filter(
        task_class="substitute_response")


def active_nomination(request_id: int) -> SubstituteNomination | None:
    """The request's current substitute nomination, if any."""
    return SubstituteNomination.objects.filter(
        request_id=request_id, is_active=True).first()
