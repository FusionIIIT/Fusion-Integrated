"""Ledger and balance computation service."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from modules.elm.domain import categories as c
from modules.elm.domain import state_machine as sm
from modules.elm.models import LeaveRequest, LedgerEntry
from modules.elm.selectors.config import effective_policy


@transaction.atomic
def ensure_annual_credits(user_id: int, kind: str, year: int | None = None) -> None:
    yr = year or timezone.localdate().year
    _, policy = effective_policy()
    if policy is None or kind not in c.EMPLOYEE_KINDS:
        return
    for cat in c.ALL:
        credit = policy.annual_credit_for(kind, cat)
        if credit > 0:
            LedgerEntry.objects.get_or_create(
                user_id=user_id,
                category=cat,
                year=yr,
                entry_type=LedgerEntry.ANNUAL_CREDIT,
                defaults={"delta": credit, "note": f"{yr} annual entitlement"},
            )


def get_available_balance(
    user_id: int, category: str, kind: str = "", exclude_request_id: int | None = None
) -> Decimal:
    """Available balance = current total ledger balance minus pending applications."""
    if kind in c.EMPLOYEE_KINDS:
        ensure_annual_credits(user_id, kind)
    total_ledger = (
        LedgerEntry.objects.filter(user_id=user_id, category=category).aggregate(
            total=Sum("delta")
        )["total"]
        or Decimal("0.00")
    )
    pending_qs = LeaveRequest.objects.filter(
        user_id=user_id, category=category, status__in=list(sm.PENDING)
    )
    if exclude_request_id:
        pending_qs = pending_qs.exclude(pk=exclude_request_id)
    pending_total = pending_qs.aggregate(total=Sum("days"))["total"] or Decimal("0.00")
    return total_ledger - pending_total


def get_account(user_id: int, kind: str = "") -> dict:
    if kind in c.EMPLOYEE_KINDS:
        ensure_annual_credits(user_id, kind)
    sums = dict(
        LedgerEntry.objects.filter(user_id=user_id)
        .values_list("category")
        .annotate(total=Sum("delta"))
    )
    pend = dict(
        LeaveRequest.objects.filter(user_id=user_id, status__in=list(sm.PENDING))
        .values_list("category")
        .annotate(total=Sum("days"))
    )
    balances = {cat: sums.get(cat) or Decimal("0.00") for cat in c.ALL}
    pending = {cat: pend.get(cat) or Decimal("0.00") for cat in c.ALL}
    available = {cat: balances[cat] - pending[cat] for cat in c.ALL}
    history = list(LedgerEntry.objects.filter(user_id=user_id).order_by("-at", "-id"))
    return {
        "user_id": user_id,
        "balances": balances,
        "pending": pending,
        "available": available,
        "history": history,
    }
