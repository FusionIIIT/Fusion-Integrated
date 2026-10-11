"""Leave-account ledger writes and reads (SRS-EL-007, SRS-EL-053, SRS-EL-087)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db.models import Sum

from modules.directory import contracts as directory
from modules.leave.domain.categories import CARRY_FORWARD, CATEGORIES, EL, VL
from modules.leave.domain.eligibility import PolicySnapshot
from modules.leave.domain.ledger import CREDIT, annual_credit
from modules.leave.models import LeaveLedgerEntry


def employee_kind(user_id: int) -> str:
    person = directory.get_users([user_id]).get(user_id)
    kind = (person.kind if person else "") or ""
    return kind if kind in ("faculty", "staff") else "staff"


def _sum(user_id: int, category: str, year: int) -> Decimal:
    qs = LeaveLedgerEntry.objects.filter(user_id=user_id, category=category)
    if category not in CARRY_FORWARD and category != EL:
        qs = qs.filter(year=year)
    total = qs.aggregate(v=Sum("amount"))["v"]
    return total or Decimal("0")


def balance(user_id: int, category: str, year: int) -> Decimal:
    return _sum(user_id, category, year)


def balances(user_id: int, year: int) -> dict[str, Decimal]:
    return {cat: balance(user_id, cat, year) for cat in CATEGORIES}


def ensure_year_credits(user_id: int, year: int, policy: PolicySnapshot) -> None:
    kind = employee_kind(user_id)
    for cat in CATEGORIES:
        credit = annual_credit(kind, cat, policy)
        if credit <= 0:
            continue
        exists = LeaveLedgerEntry.objects.filter(
            user_id=user_id, category=cat, year=year, entry_type=CREDIT,
        ).exists()
        if exists:
            continue
        LeaveLedgerEntry.objects.create(
            user_id=user_id, category=cat, year=year, amount=credit,
            entry_type=CREDIT, memo=f"Annual {cat} credit for {year}",
        )


def post(*, user_id: int, category: str, year: int, amount: Decimal,
         entry_type: str, memo: str, application=None) -> LeaveLedgerEntry:
    return LeaveLedgerEntry.objects.create(
        user_id=user_id, category=category, year=year, amount=amount,
        entry_type=entry_type, memo=memo, application=application,
    )


def history(user_id: int):
    return (LeaveLedgerEntry.objects.filter(user_id=user_id)
            .order_by("-created_at", "-id"))
