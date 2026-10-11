"""Every read elm needs, batched. No writes live in this package."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from modules.elm.models import Holiday, LeaveBalanceEntry, LeaveType

ZERO = Decimal("0")
_KINDS = ("grant", "credit", "debit", "reversal")


@dataclass(frozen=True)
class Balance:
    """One bucket as a person should read it: entitled, used, available."""

    leave_type: LeaveType
    entitled: Decimal
    used: Decimal
    available: Decimal


def types_effective_on(on: date) -> list[LeaveType]:
    """The latest active version of every type effective on that date (BR-12)."""
    rows = (LeaveType.objects
            .filter(is_active=True, effective_from__lte=on)
            .order_by("code", "-effective_from"))
    seen: dict[str, LeaveType] = {}
    for row in rows:
        seen.setdefault(row.code, row)
    return sorted(seen.values(), key=lambda t: (t.name, t.code))


def holidays_between(start: date, end: date) -> set[date]:
    return set(Holiday.objects.filter(date__gte=start, date__lte=end)
               .values_list("date", flat=True))


def ledger_totals(user_ids: Sequence[int], year: int
                  ) -> dict[tuple[int, str], dict[str, Decimal]]:
    """Signed sums per (person, leave-type code) for one year, in one query.

    Keyed by code, not by version id: a type superseded mid-year must not split
    the balance into two buckets.
    """
    ids = [int(i) for i in user_ids if i is not None]
    if not ids:
        return {}
    rows = (LeaveBalanceEntry.objects
            .filter(user_id__in=ids, year=year)
            .values("user_id", "leave_type__code", "kind")
            .annotate(total=Sum("days")))
    totals: dict[tuple[int, str], dict[str, Decimal]] = {}
    for row in rows:
        bucket = totals.setdefault((row["user_id"], row["leave_type__code"]),
                                   dict.fromkeys(_KINDS, ZERO))
        bucket[row["kind"]] = row["total"] or ZERO
    return totals


def _balance(leave_type: LeaveType, totals: dict[str, Decimal] | None) -> Balance:
    bucket = totals or dict.fromkeys(_KINDS, ZERO)
    entitled = bucket["grant"] + bucket["credit"]
    used = -(bucket["debit"] + bucket["reversal"])
    return Balance(leave_type, entitled, used, entitled - used)


def balances_for(user_id: int, year: int, *, on: date | None = None) -> list[Balance]:
    """One person's buckets for a year, including types with no movements."""
    day = on or timezone.localdate()
    totals = ledger_totals([user_id], year)
    return [_balance(t, totals.get((user_id, t.code)))
            for t in types_effective_on(day)]


def balances_for_users(user_ids: Sequence[int], year: int, *,
                       on: date | None = None) -> dict[int, list[Balance]]:
    """The batched form contracts call; one query for every ledger total."""
    ids = sorted({int(i) for i in user_ids if i is not None})
    if not ids:
        return {}
    day = on or timezone.localdate()
    types = types_effective_on(day)
    totals = ledger_totals(ids, year)
    return {uid: [_balance(t, totals.get((uid, t.code))) for t in types]
            for uid in ids}


def available_days(user_id: int, leave_type_code: str, year: int) -> Decimal:
    """What the approval guard consumes (BR-07)."""
    totals = ledger_totals([user_id], year).get((user_id, leave_type_code))
    bucket = totals or dict.fromkeys(_KINDS, ZERO)
    return bucket["grant"] + bucket["credit"] + bucket["debit"] + bucket["reversal"]
