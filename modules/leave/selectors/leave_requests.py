"""Selectors for Leave Management — ALL reads go here."""
from datetime import date
from typing import Optional

from django.db.models import Q, QuerySet

from ..models import (
    HolidayCalendar,
    LeaveBalance,
    LeavePolicy,
    LeaveRequest,
    LeaveRequestTransition,
    OfflineLeaveEntry,
    SubstituteRequest,
)
from ..domain.entities import LeaveCategory, LeaveStatus


def get_leave_policy(category: str, employee_type: str, on_date: date) -> Optional[LeavePolicy]:
    """Get effective leave policy for category and employee type on a given date."""
    return LeavePolicy.objects.filter(
        category=category,
        employee_type=employee_type,
        effective_from__lte=on_date,
        is_active=True,
    ).filter(
        Q(effective_to__isnull=True) | Q(effective_to__gte=on_date)
    ).order_by("-effective_from").first()


def get_leave_balance(user_id: int, category: str, year: int) -> Optional[LeaveBalance]:
    """Get leave balance for user, category, and year."""
    return LeaveBalance.objects.filter(
        user_id=user_id,
        category=category,
        year=year,
    ).first()


def get_user_balances(user_id: int, year: int) -> QuerySet[LeaveBalance]:
    """Get all leave balances for a user in a year."""
    return LeaveBalance.objects.filter(user_id=user_id, year=year)


def get_holiday_calendar(year: int, is_restricted: Optional[bool] = None) -> QuerySet[HolidayCalendar]:
    """Get holiday calendar for a year."""
    qs = HolidayCalendar.objects.filter(year=year, is_active=True)
    if is_restricted is not None:
        qs = qs.filter(is_restricted=is_restricted)
    return qs.order_by("date")


def is_holiday(date_obj: date, is_restricted: bool = False) -> bool:
    """Check if a date is a holiday (or RH)."""
    return HolidayCalendar.objects.filter(
        date=date_obj,
        is_restricted=is_restricted,
        is_active=True,
    ).exists()


def visible_leave_requests(principal) -> QuerySet[LeaveRequest]:
    """Return leave requests visible to the principal based on permissions."""
    qs = LeaveRequest.objects.select_related("extension_of", "original_request")

    if principal.has_permission("leave_management.leave_request.view"):
        # Can see all (within scope - scope filtering would go here)
        return qs

    if principal.has_permission("leave_management.leave_request.view_self"):
        return qs.filter(user_id=principal.user_id)

    return qs.none()


def get_leave_request(request_id: int, principal) -> Optional[LeaveRequest]:
    """Get a single leave request if visible to principal."""
    return visible_leave_requests(principal).filter(pk=request_id).first()


def get_user_leave_requests(
    user_id: int,
    principal,
    status: Optional[str] = None,
    category: Optional[str] = None,
) -> QuerySet[LeaveRequest]:
    """Get leave requests for a specific user (with permission check)."""
    qs = visible_leave_requests(principal).filter(user_id=user_id)
    if status:
        qs = qs.filter(status=status)
    if category:
        qs = qs.filter(category=category)
    return qs.order_by("-created_at")


def get_pending_approvals(principal) -> QuerySet[LeaveRequest]:
    """Get leave requests pending approval by this principal."""
    qs = LeaveRequest.objects.none()

    if principal.has_permission("leave_management.leave_request.approve"):
        # Unit Head can see requests in unit_head_review
        qs = qs | LeaveRequest.objects.filter(status=LeaveStatus.UNIT_HEAD_REVIEW)

        # Establishment can see requests in establishment_review
        qs = qs | LeaveRequest.objects.filter(status=LeaveStatus.ESTABLISHMENT_REVIEW)

        # Final authority can see requests in final_sanction
        qs = qs | LeaveRequest.objects.filter(status=LeaveStatus.FINAL_SANCTION)

    return qs.distinct().order_by("created_at")


def get_substitute_requests_for_user(user_id: int, status: Optional[str] = None) -> QuerySet[SubstituteRequest]:
    """Get substitute requests where user is the nominee."""
    qs = SubstituteRequest.objects.select_related("leave_request").filter(substitute_id=user_id)
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-created_at")


def get_pending_substitute_requests(user_id: int) -> QuerySet[SubstituteRequest]:
    """Get pending substitute requests for a user."""
    return get_substitute_requests_for_user(user_id, status="pending")


def get_leave_request_history(request_id: int) -> QuerySet[LeaveRequestTransition]:
    """Get audit trail for a leave request."""
    return LeaveRequestTransition.objects.filter(leave_request_id=request_id).order_by("created_at")


def get_offline_leave_entries(user_id: int) -> QuerySet[OfflineLeaveEntry]:
    """Get offline leave entries for a user."""
    return OfflineLeaveEntry.objects.filter(user_id=user_id).order_by("-start_date")


def get_overlapping_requests(
    user_id: int,
    start_date: date,
    end_date: date,
    exclude_id: Optional[int] = None,
) -> QuerySet[LeaveRequest]:
    """Find overlapping approved or pending leave requests."""
    qs = LeaveRequest.objects.filter(
        user_id=user_id,
        start_date__lte=end_date,
        end_date__gte=start_date,
        status__in=[
            LeaveStatus.SUBMITTED,
            LeaveStatus.SUBSTITUTE_PENDING,
            LeaveStatus.UNIT_HEAD_REVIEW,
            LeaveStatus.ESTABLISHMENT_REVIEW,
            LeaveStatus.FINAL_SANCTION,
            LeaveStatus.APPROVED,
        ],
    )
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    return qs