"""Read-only queries for ELM data."""

from modules.elm.models import (
    EmployeeLeaveBalance,
    LeaveApplication,
    LeaveCategory,
)

PENDING_STATUSES = (
    "submitted",
    "unit_head_review",
    "recommended",
    "not_recommended",
    "establishment_review",
)


def get_leave_categories():
    return LeaveCategory.objects.all().order_by("code")


def get_employee_balance(user_id):
    return {
        balance.leave_category.code: balance
        for balance in EmployeeLeaveBalance.objects.select_related("leave_category")
        .filter(user_id=user_id)
        .order_by("leave_category__code")
    }


def get_applications(user_id):
    return (
        LeaveApplication.objects.select_related("leave_category")
        .filter(user_id=user_id)
        .order_by("-created_at", "-pk")
    )


def get_pending_applications(user_id):
    return get_applications(user_id).filter(status__in=PENDING_STATUSES)


def get_application(application_id):
    return (
        LeaveApplication.objects.select_related("leave_category").filter(pk=application_id).first()
    )
