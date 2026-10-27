"""Selectors for querying leave balances, requests, and calendars."""
from datetime import date
from typing import List, Tuple, Set
from django.db.models import QuerySet

from modules.elm.models import (
    LeaveBalance,
    LeaveRequest,
    HolidayCalendar,
    AcademicVacationPeriod,
    LeaveStatus,
    SubstituteStatus,
)


def get_user_balances(user_id: int, year: int) -> QuerySet[LeaveBalance]:
    return LeaveBalance.objects.filter(user_id=user_id, year=year)


def get_user_leave_requests(user_id: int) -> QuerySet[LeaveRequest]:
    return LeaveRequest.objects.filter(user_id=user_id).order_by("-created_at")


def get_leave_request_by_id(leave_id: int) -> LeaveRequest:
    return LeaveRequest.objects.get(id=leave_id)


def get_pending_substitute_requests(substitute_user_id: int) -> QuerySet[LeaveRequest]:
    return LeaveRequest.objects.filter(
        substitute_user_id=substitute_user_id,
        substitute_status=SubstituteStatus.PENDING,
        current_status=LeaveStatus.PENDING_SUBSTITUTE,
    ).order_by("-created_at")


def get_pending_unit_head_approvals() -> QuerySet[LeaveRequest]:
    return LeaveRequest.objects.filter(
        current_status=LeaveStatus.PENDING_UNIT_HEAD
    ).order_by("-created_at")


def get_pending_sanction_approvals() -> QuerySet[LeaveRequest]:
    return LeaveRequest.objects.filter(
        current_status=LeaveStatus.PENDING_SANCTION
    ).order_by("-created_at")


def get_published_rh_dates(year: int) -> Set[date]:
    return set(
        HolidayCalendar.objects.filter(
            year=year,
            holiday_type=HolidayCalendar.HolidayType.RESTRICTED,
            is_published=True,
        ).values_list("date", flat=True)
    )


def get_closed_holiday_dates(year: int) -> Set[date]:
    return set(
        HolidayCalendar.objects.filter(
            year=year,
            holiday_type=HolidayCalendar.HolidayType.CLOSED,
            is_published=True,
        ).values_list("date", flat=True)
    )


def get_active_vacation_intervals() -> List[Tuple[date, date]]:
    return list(
        AcademicVacationPeriod.objects.filter(is_active=True).values_list(
            "start_date", "end_date"
        )
    )


def get_active_user_leaves(user_id: int) -> List[Tuple[date, date, str]]:
    """Return active (pending or approved) leaves for overlap checking."""
    active_statuses = [
        LeaveStatus.PENDING_SUBSTITUTE,
        LeaveStatus.PENDING_UNIT_HEAD,
        LeaveStatus.PENDING_ESTT,
        LeaveStatus.PENDING_SANCTION,
        LeaveStatus.APPROVED,
        LeaveStatus.CANCELLATION_PENDING,
    ]
    return list(
        LeaveRequest.objects.filter(
            user_id=user_id,
            current_status__in=active_statuses,
        ).values_list("start_date", "end_date", "half_day")
    )
