"""Query selectors for Employee Leave Management."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.elm.models import HolidayCalendar, LeaveApplication, LeaveBalance, SubstituteRequest
from modules.elm.services import ensure_default_balances


def get_user_balances(user_id: int) -> QuerySet[LeaveBalance]:
    ensure_default_balances(user_id)
    return LeaveBalance.objects.filter(user_id=user_id).order_by("leave_type")


def get_user_applications(user_id: int) -> QuerySet[LeaveApplication]:
    return LeaveApplication.objects.filter(user_id=user_id).order_by("-created_at")


def get_approval_queue() -> QuerySet[LeaveApplication]:
    return LeaveApplication.objects.filter(status="PENDING").order_by("created_at")


def get_holidays() -> QuerySet[HolidayCalendar]:
    return HolidayCalendar.objects.all().order_by("date")


def get_substitute_requests(user_id: int) -> QuerySet[SubstituteRequest]:
    return (
        SubstituteRequest.objects.filter(substitute_user_id=user_id)
        .select_related("leave_application")
        .order_by("-created_at")
    )

