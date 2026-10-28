"""All ELM reads. Ownership and scope filtering live here, once per module —
a foreign id therefore yields 404 rather than 403 (existence is not leaked).
"""
from __future__ import annotations

from django.db.models import QuerySet

from modules.leave.models import (
    Holiday,
    LeaveAccount,
    LeaveApplication,
    LeavePolicy,
    LeaveTask,
    VacationPeriod,
)


def visible_applications(principal) -> QuerySet[LeaveApplication]:
    qs = LeaveApplication.objects.all()
    if principal.has_permission("leave_management.leave.view"):
        return qs
    return qs.filter(applicant_user_id=principal.user_id)


def my_accounts(user_id: int, year: int) -> QuerySet[LeaveAccount]:
    return LeaveAccount.objects.filter(user_id=user_id, year=year)


def my_accounts_all(user_id: int) -> QuerySet[LeaveAccount]:
    return LeaveAccount.objects.filter(user_id=user_id).order_by("-year")


def published_holidays() -> QuerySet[Holiday]:
    return Holiday.objects.filter(published=True)


def closed_holiday_dates() -> frozenset:
    return frozenset(
        Holiday.objects.filter(published=True, kind="closed")
        .values_list("on_date", flat=True))


def restricted_holiday_dates() -> frozenset:
    return frozenset(
        Holiday.objects.filter(published=True, kind="restricted")
        .values_list("on_date", flat=True))


def active_vacations() -> QuerySet[VacationPeriod]:
    return VacationPeriod.objects.all()


def policies() -> QuerySet[LeavePolicy]:
    return LeavePolicy.objects.all()


def open_tasks() -> QuerySet[LeaveTask]:
    return LeaveTask.objects.filter(is_open=True)
