from typing import List
from modules.elm.models import LeaveRequest, LeaveBalance, LeaveStatus


def get_user_leaves(user_id: str) -> List[LeaveRequest]:
    return LeaveRequest.objects.filter(applicant_user_id=user_id).order_by("-created_at")


def get_user_balances(user_id: str, year: int = 2026) -> List[LeaveBalance]:
    return LeaveBalance.objects.filter(user_id=user_id, year=year)


def get_pending_substitute_requests(user_id: str) -> List[LeaveRequest]:
    return LeaveRequest.objects.filter(
        substitute_user_id=user_id,
        status=LeaveStatus.PENDING_SUBSTITUTE,
    ).order_by("-created_at")


def get_pending_unit_head_approvals() -> List[LeaveRequest]:
    return LeaveRequest.objects.filter(
        status=LeaveStatus.PENDING_UNIT_HEAD,
    ).order_by("created_at")
