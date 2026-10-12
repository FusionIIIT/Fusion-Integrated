"""Balance reads, computed from the ledger."""
from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum

from modules.elm.domain import categories as c
from modules.elm.domain import state_machine as sm
from modules.elm.models import LeaveRequest, LedgerEntry


def balances(user_id: int) -> dict[str, Decimal]:
    rows = (LedgerEntry.objects.filter(user_id=user_id)
            .values("category").annotate(total=Sum("delta")))
    out = {cat: Decimal("0") for cat in c.ALL}
    for r in rows:
        out[r["category"]] = r["total"] or Decimal("0")
    return out


def pending_days(user_id: int, exclude_id: int | None = None) -> dict[str, Decimal]:
    qs = LeaveRequest.objects.filter(user_id=user_id, status__in=sm.PENDING)
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    out = {cat: Decimal("0") for cat in c.ALL}
    for r in qs.values("category").annotate(total=Sum("days")):
        out[r["category"]] = r["total"] or Decimal("0")
    return out


def history(user_id: int):
    return (LedgerEntry.objects.filter(user_id=user_id)
            .select_related("request").order_by("-at", "-id"))
