"""Scoped read-side selectors for the ELM module."""

from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from modules.elm.models import (
    LeaveAccount,
    LeaveCategory,
    LeaveRequest,
    LeaveReservation,
    WorkflowTask,
)


def balances(*, user_id, year=None):
    year = year or timezone.localdate().year
    result = []
    for category in LeaveCategory.objects.filter(is_active=True).order_by("code"):
        account = LeaveAccount.objects.filter(user_id=user_id, category=category, year=year).first()
        if not account:
            result.append({"category": category.code, "year": year, "configured": False})
            continue
        reserved = LeaveReservation.objects.filter(account=account, is_active=True).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")
        ledger = account.transactions.aggregate(total=Sum("amount"))["total"] or Decimal("0")
        available = account.annual_entitlement + account.opening_balance + ledger - reserved
        result.append(
            {
                "category": category.code,
                "year": year,
                "configured": True,
                "annual_entitlement": str(account.annual_entitlement),
                "opening_balance": str(account.opening_balance),
                "ledger_total": str(ledger),
                "reserved": str(reserved),
                "available": str(available),
            }
        )
    return result


def history(*, user_id):
    return (
        LeaveRequest.objects.filter(employee_user_id=user_id)
        .select_related("category")
        .prefetch_related("events")
        .order_by("-created_at")
    )


def tasks_for(*, user_id):
    return (
        WorkflowTask.objects.filter(
            assigned_to_user_id=user_id, status="pending", request__isnull=False
        )
        .select_related("request", "request__category")
        .order_by("assigned_at")
    )


def export_rows(*, user_id):
    return history(user_id=user_id).values_list(
        "id",
        "category__code",
        "starts_on",
        "ends_on",
        "chargeable_days",
        "status",
        "reason",
        "created_at",
    )
