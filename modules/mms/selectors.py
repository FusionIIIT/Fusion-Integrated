"""Query selectors for Mess Management System (MMS)."""

from typing import Optional
from django.db.models import QuerySet
from modules.mms.models import (
    DailyMenuItem,
    MessActionLog,
    MessFeedback,
    MessRegistration,
    MessRoleAssignment,
    RebateRequest,
    RegistrationWindow,
)


def get_active_roles(mess_name: Optional[str] = None) -> QuerySet[MessRoleAssignment]:
    qs = MessRoleAssignment.objects.filter(is_active=True)
    if mess_name:
        qs = qs.filter(mess_name=mess_name)
    return qs


def get_open_registration_windows() -> QuerySet[RegistrationWindow]:
    return RegistrationWindow.objects.filter(is_open=True).order_by("-start_date")


def get_student_registrations(student_id: int) -> QuerySet[MessRegistration]:
    return MessRegistration.objects.filter(student_id=student_id).order_by("-created_at")


def get_weekly_menu(mess_name: str) -> QuerySet[DailyMenuItem]:
    return DailyMenuItem.objects.filter(mess_name=mess_name).order_by("day_of_week", "meal_time")


def get_student_rebates(student_id: int) -> QuerySet[RebateRequest]:
    return RebateRequest.objects.filter(student_id=student_id).order_by("-start_date")


def get_mess_rebates(mess_name: Optional[str] = None) -> QuerySet[RebateRequest]:
    qs = RebateRequest.objects.all().order_by("-start_date")
    if mess_name:
        qs = qs.filter(mess_name=mess_name)
    return qs


def get_feedbacks(mess_name: Optional[str] = None) -> QuerySet[MessFeedback]:
    qs = MessFeedback.objects.all().order_by("-created_at")
    if mess_name:
        qs = qs.filter(mess_name=mess_name)
    return qs


def get_action_logs() -> QuerySet[MessActionLog]:
    return MessActionLog.objects.all().order_by("-created_at")

