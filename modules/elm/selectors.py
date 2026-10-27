"""Read queries scoped to the authenticated applicant."""

from modules.elm.models import LeaveRequest


def requests_for_applicant(principal):
    return (
        LeaveRequest.objects.filter(user_id=principal.user_id)
        .prefetch_related("workflow_actions")
        .order_by("-id")
    )
