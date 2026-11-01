"""Reads over leave accounts: the balance projection and what is committed."""
from __future__ import annotations

from decimal import Decimal

from modules.leave.domain import categories as cat
from modules.leave.domain import ledger as led
from modules.leave.domain import state_machine as sm
from modules.leave.models import LeaveAccount, LeaveLedgerEntry, LeaveRequest

ZERO = Decimal("0")


def account(*, user_id: int, year: int, category: str) -> LeaveAccount | None:
    return LeaveAccount.objects.filter(user_id=user_id, year=year,
                                       category=category).first()


def balance(*, user_id: int, year: int, category: str) -> Decimal:
    """The ledger projection. An account nobody has touched yet is zero."""
    row = account(user_id=user_id, year=year, category=category)
    if row is None:
        return ZERO
    return led.project(row.entries.values_list("entry_type", "days").order_by("id"))


def balances(*, user_id: int, year: int) -> dict[str, Decimal]:
    return {c: balance(user_id=user_id, year=year, category=c)
            for c in cat.CATEGORIES}


def committed(*, user_id: int, year: int, category: str) -> Decimal:
    """Days already promised to requests that have not been posted yet.

    Without this a person can file five separate five-day requests against a
    balance of five, and all five look affordable on their own.
    """
    rows = (LeaveRequest.objects
            .filter(user_id=user_id, category=category,
                    start_date__year__lte=year, end_date__year__gte=year,
                    status__in=tuple(sorted(sm.PENDING)),
                    approved_days_posted=False)
            .values_list("days_requested", flat=True))
    return sum((Decimal(str(d)) for d in rows), ZERO)


def available(*, user_id: int, year: int, category: str) -> Decimal:
    return led.available(balance(user_id=user_id, year=year, category=category),
                         committed(user_id=user_id, year=year, category=category))


def ledger_for(*, user_id: int, year: int | None = None,
               category: str = "") -> list[LeaveLedgerEntry]:
    qs = LeaveLedgerEntry.objects.filter(account__user_id=user_id) \
        .select_related("account")
    if year is not None:
        qs = qs.filter(account__year=year)
    if category:
        qs = qs.filter(account__category=category)
    return list(qs.order_by("id"))


def accounts_for_year(year: int):
    return LeaveAccount.objects.filter(year=year).order_by("user_id", "category")
