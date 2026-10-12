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
    history = list(LedgerEntry.objects.filter(user_id=user_id).order_by("-at", "-id"))
    return {
        "user_id": user_id,
        "balances": balances,
        "pending": pending,
        "history": history,
    }
