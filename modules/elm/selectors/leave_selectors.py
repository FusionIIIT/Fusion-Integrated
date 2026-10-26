from django.utils import timezone

from modules.elm.models import LeaveBalance, LeaveRequest, LeaveStatus


def get_user_leaves(user_id: str) -> list[LeaveRequest]:
    return LeaveRequest.objects.filter(applicant_user_id=user_id).order_by("-created_at")


def get_user_balances(user_id: str, year: int | None = None) -> list[LeaveBalance]:
    if year is None:
        year = timezone.localdate().year
    return LeaveBalance.objects.filter(user_id=user_id, year=year)


def get_pending_substitute_requests(user_id: str) -> list[LeaveRequest]:
    return LeaveRequest.objects.filter(
        substitute_user_id=user_id,
        status=LeaveStatus.PENDING_SUBSTITUTE,
    ).order_by("-created_at")


def get_pending_approvals(approver_role: str) -> list[LeaveRequest]:
    if approver_role == "director":
        status = LeaveStatus.PENDING_AUTHORITY
    elif approver_role in {"unit_head", "dean", "registrar", "leave_admin"}:
        status = LeaveStatus.PENDING_UNIT_HEAD
    else:
        return LeaveRequest.objects.none()
    return LeaveRequest.objects.filter(
        status=status,
        current_approver_role=approver_role if approver_role == "director" else "unit_head",
    ).order_by("created_at")
