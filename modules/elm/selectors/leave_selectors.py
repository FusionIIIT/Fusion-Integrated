from django.utils import timezone

from modules.elm.models import LeaveBalance, LeaveRequest, LeaveStatus


def get_user_leaves(user_id: str) -> list[LeaveRequest]:
    return LeaveRequest.objects.filter(applicant_user_id=user_id).order_by("-created_at")


def get_user_balances(user_id: str, year: int | None = None) -> list[LeaveBalance]:
    year = year or timezone.localdate().year
    return LeaveBalance.objects.filter(user_id=user_id, year=year)


def get_pending_substitute_requests(user_id: str) -> list[LeaveRequest]:
    return LeaveRequest.objects.filter(
        substitute_user_id=user_id,
        status=LeaveStatus.PENDING_SUBSTITUTE,
    ).order_by("-created_at")


def get_pending_unit_head_approvals() -> list[LeaveRequest]:
    return LeaveRequest.objects.filter(
        status=LeaveStatus.PENDING_UNIT_HEAD,
        current_approver_role="unit_head",
    ).order_by("created_at")


def get_pending_authority_approvals() -> list[LeaveRequest]:
    return LeaveRequest.objects.filter(
        status=LeaveStatus.PENDING_AUTHORITY,
        current_approver_role__in=("director", "sanctioning_authority"),
    ).order_by("created_at")
