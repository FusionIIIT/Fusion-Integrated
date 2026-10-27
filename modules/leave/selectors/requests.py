"""Ownership-scoped leave reads."""
from modules.leave.models import LeaveRequest


def visible_requests(principal):
    return LeaveRequest.objects.filter(user_id=principal.user_id)


def visible_request(*, principal, request_id: int):
    return visible_requests(principal).filter(pk=request_id).first()
