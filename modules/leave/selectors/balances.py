"""Balances and history read models (EL-UC-012); balances are sums of the ledger."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Sum

from modules.leave.domain import categories as cat
from modules.leave.models import PENDING_STATES, LeaveRequest, LedgerEntry


def balances(user_ids, year: int) -> dict[int, dict[str, Decimal]]:
    ids = [int(i) for i in user_ids]
    out: dict[int, dict[str, Decimal]] = {i: dict.fromkeys(cat.ALL, Decimal(0)) for i in ids}
    rows = (LedgerEntry.objects.filter(user_id__in=ids, leave_year=year)
            .values("user_id", "category").annotate(total=Sum("delta")))
    for r in rows:
        out[r["user_id"]][r["category"]] = r["total"]
    return out


def pending_charges(user_ids, year: int, *, exclude_request_id: int | None = None
                    ) -> dict[int, dict[str, Decimal]]:
    """Days already asked for and not yet decided, so two requests cannot spend one balance."""
    ids = [int(i) for i in user_ids]
    out: dict[int, dict[str, Decimal]] = defaultdict(lambda: dict.fromkeys(cat.ALL, Decimal(0)))
    qs = LeaveRequest.objects.filter(user_id__in=ids, leave_year=year,
                                     status__in=PENDING_STATES, kind__in=("new", "extension"))
    if exclude_request_id:
        qs = qs.exclude(pk=exclude_request_id)
    for r in qs.values("user_id", "category").annotate(total=Sum("days")):
        out[r["user_id"]][r["category"]] = r["total"]
    return {i: out[i] for i in ids}


@dataclass(frozen=True)
class BalanceRow:
    category: str
    label: str
    balance: Decimal
    pending: Decimal
    available: Decimal
    applicable: bool


def overview(user_id: int, kind: str, year: int) -> list[BalanceRow]:
    held = balances([user_id], year)[user_id]
    asked = pending_charges([user_id], year)[user_id]
    return [BalanceRow(code, cat.LABELS[code], held[code], asked[code], held[code] - asked[code],
                       cat.applicable(code, kind)) for code in cat.ALL]


def ledger(user_id: int, year: int | None = None):
    qs = LedgerEntry.objects.filter(user_id=user_id).order_by("-created_at", "-id")
    return qs.filter(leave_year=year) if year else qs
