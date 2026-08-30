"""Balances, derived from the ledger rather than stored.

Every figure here is a sum over `leave_ledger_entry`. Nothing caches it. The
cost is one grouped query; the return is that a balance can always be explained
by listing the rows behind it, and can never disagree with them.
"""
from __future__ import annotations

from decimal import Decimal

from django.db.models import Q, QuerySet, Sum

from modules.leave.domain.categories import Category
from modules.leave.domain.entitlement import Balance
from modules.leave.models import EntryReason, LedgerEntry

ZERO = Decimal("0")

#: Which reasons count towards which side of a balance.
_ADDS = (
    EntryReason.ANNUAL_CREDIT,
    EntryReason.OPENING_BALANCE,
    EntryReason.CONVERTED_IN,
)
_RESTORES = (EntryReason.RESTORED, EntryReason.CANCELLED)


def entries_for(user_id: int, year: int) -> QuerySet[LedgerEntry]:
    return LedgerEntry.objects.filter(user_id=user_id, year=year)


def balances_for(user_id: int, year: int) -> dict[Category, Balance]:
    """Every category this person holds in this year."""
    rows = (
        entries_for(user_id, year)
        .values("category")
        .annotate(
            credited=Sum("days", filter=Q(reason__in=_ADDS)),
            restored=Sum("days", filter=Q(reason__in=_RESTORES)),
            consumed=Sum("days", filter=Q(reason=EntryReason.CONSUMED)),
            offline=Sum("days", filter=Q(reason=EntryReason.OFFLINE_RECORDED)),
            corrected=Sum("days", filter=Q(reason=EntryReason.CORRECTION)),
            lapsed=Sum("days", filter=Q(reason=EntryReason.LAPSED)),
            converted_out=Sum("days", filter=Q(reason=EntryReason.CONVERTED_OUT)),
        )
    )
    out: dict[Category, Balance] = {}
    for row in rows:
        category = Category(row["category"])
        credited = (row["credited"] or ZERO) + (row["corrected"] or ZERO)
        # Consumption, lapse and conversion out are stored as negative days, so
        # they subtract by addition and the ledger always sums to the balance.
        spent = -(
            (row["consumed"] or ZERO)
            + (row["offline"] or ZERO)
            + (row["lapsed"] or ZERO)
            + (row["converted_out"] or ZERO)
        )
        out[category] = Balance(
            category=category,
            opening=ZERO,
            credited=credited,
            consumed=spent,
            restored=row["restored"] or ZERO,
        )
    return out


def balance_for(user_id: int, year: int, category: Category) -> Balance:
    return balances_for(user_id, year).get(category, Balance(category=category))


def available(user_id: int, year: int, category: Category) -> Decimal:
    return balance_for(user_id, year, category).available


def statement(user_id: int, year: int, category: Category) -> list[LedgerEntry]:
    """The rows behind a balance, oldest first. EL-UC-012."""
    return list(entries_for(user_id, year).filter(category=category).order_by("id"))
