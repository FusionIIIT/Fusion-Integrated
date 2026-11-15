from django.db.models import QuerySet

from modules.elm.models import LeaveRequest, WorkflowTask


def for_applicant(user_id: int) -> QuerySet[LeaveRequest]:
    return LeaveRequest.objects.filter(
        applicant_user_id=user_id,
    ).prefetch_related("tasks", "events").order_by("-submitted_at", "-pk")


def applicant_request(request_id: int, user_id: int) -> QuerySet[LeaveRequest]:
    return LeaveRequest.objects.filter(
        pk=request_id, applicant_user_id=user_id,
    ).prefetch_related("tasks", "events")


def for_substitute(user_id: int) -> QuerySet[LeaveRequest]:
    return LeaveRequest.objects.filter(
        substitute_user_id=user_id,
        status="substitute_pending",
    ).prefetch_related("tasks", "events").order_by("submitted_at", "pk")


def assigned_pending_tasks(user_id: int) -> QuerySet[WorkflowTask]:
    return WorkflowTask.objects.filter(
        assigned_user_id=user_id,
        status="pending",
    ).select_related("request").prefetch_related(
        "request__tasks", "request__events",
    ).order_by("assigned_at", "pk")
