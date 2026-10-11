"""Ledger writes. Every balance change is a new row (append-only)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import connection, transaction

from modules.elm.domain import policy
from modules.elm.models import CategoryPolicy, LedgerEntry
from modules.elm.selectors import accounts as acc


def lock_account(user_id: int) -> None:
    """Serialise balance changes per person for the rest of the transaction."""
    with connection.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(%s, %s)", [7301, int(user_id)])


def ensure_annual_credits(user_id: int, kind: str, year: int) -> None:
    """BR-EL-002/003/004/005/006/009: credit the year's entitlement once."""
    entitlements = dict(CategoryPolicy.objects.values_list("category",
                                                           "annual_days"))
    for category in policy.credited_categories(kind):
        days = entitlements.get(category)
        if days is None:
            continue
        LedgerEntry.objects.get_or_create(
            user_id=user_id, category=category, year=year,
            kind=LedgerEntry.ANNUAL_CREDIT,
            defaults={"days": days, "note": "Annual entitlement"})


def available(user_id: int, kind: str, category: str, year: int,
              exclude_request_id: int | None = None) -> Decimal:
    ensure_annual_credits(user_id, kind, year)
    return (acc.balances(user_id, year)[category]
            - acc.reserved(user_id, category, exclude_request_id))


def post(*, user_id: int, category: str, on: date, kind: str, days: Decimal,
         request=None, note: str = "", recorded_by_id: int | None = None
         ) -> LedgerEntry:
    with transaction.atomic():
        return LedgerEntry.objects.create(
            user_id=user_id, category=category, year=on.year, kind=kind,
            days=days, request=request, note=note[:300],
            recorded_by_id=recorded_by_id)
