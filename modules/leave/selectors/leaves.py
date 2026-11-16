"""Read operations with ownership and scope filtering for Leave Management."""
from __future__ import annotations

from datetime import date

from django.db.models import QuerySet

from modules.leave.models import ApprovingAuthority, LeaveBalance, LeaveRequest


def get_requests_for_user(user_id: int) -> QuerySet[LeaveRequest]:
    """Return all leave requests submitted by the given user."""
    return LeaveRequest.objects.filter(user_id=user_id).prefetch_related("decisions")


def get_balances_for_user(user_id: int, year: int | None = None) -> QuerySet[LeaveBalance]:
    """Return leave balances for the given user, optionally filtered by year."""
    current_year = year or date.today().year
    return LeaveBalance.objects.filter(user_id=user_id, year=current_year)


def get_user_balance_for_type(
    user_id: int,
    leave_type: str,
    year: int | None = None,
) -> LeaveBalance | None:
    """Return a single leave balance row for a specific leave type and year."""
    target_year = year or date.today().year
    return LeaveBalance.objects.filter(
        user_id=user_id,
        leave_type=leave_type,
        year=target_year,
    ).first()


def get_pending_requests_for_authority(authority_user_id: int) -> QuerySet[LeaveRequest]:
    """Return all leave requests waiting for this authority's decision."""
    from django.db.models import Q

    auth = get_authority_record(authority_user_id)
    if auth:
        return (
            LeaveRequest.objects.filter(
                status=LeaveRequest.Status.PENDING_CURRENT_AUTHORITY,
            )
            .filter(
                Q(current_authority_id=authority_user_id)
                | Q(current_authority_role=auth.role)
                | Q(current_authority_id__isnull=True)
            )
            .prefetch_related("decisions")
            .order_by("-created_at")
        )

    return (
        LeaveRequest.objects.filter(
            current_authority_id=authority_user_id,
            status=LeaveRequest.Status.PENDING_CURRENT_AUTHORITY,
        )
        .prefetch_related("decisions")
        .order_by("-created_at")
    )


def get_request_by_id(request_id: int) -> LeaveRequest | None:
    """Return a leave request by its primary key with preloaded decisions."""
    return (
        LeaveRequest.objects.filter(id=request_id)
        .prefetch_related("decisions")
        .first()
    )


def get_authority_record(user_id: int) -> ApprovingAuthority | None:
    """Check if the user is registered as an approving authority."""
    return ApprovingAuthority.objects.filter(user_id=user_id, is_active=True).first()
