"""The append-only leave ledger. Every write takes the per-employee lock first."""
from __future__ import annotations

from decimal import Decimal

from django.db import connection

from core.api.exceptions import ConflictError
from modules.leave.domain.accounting import Reason
from modules.leave.domain.categories import LABELS, Category, EmployeeKind, annual_credit
from modules.leave.models import LeavePolicy, LeaveRequest, LedgerEntry
from modules.leave.selectors import accounts as reads

_LOCK_NAMESPACE = 7311


def lock(user_id: int) -> None:
    """Serialises balance checks per employee for the rest of the transaction."""
    with connection.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(%s, %s)", [_LOCK_NAMESPACE, user_id])


def post(user_id: int, category: Category, year: int, days: Decimal, reason: Reason, *,
         request: LeaveRequest | None = None, key: str | None = None, note: str = "",
         by: int | None = None) -> LedgerEntry:
    fields = {"user_id": user_id, "category": category.value, "year": year, "days": days,
              "reason": reason.value, "request": request, "note": note[:255],
              "created_by_user_id": by}
    if key is None:
        return LedgerEntry.objects.create(**fields)
    entry, _ = LedgerEntry.objects.get_or_create(idempotency_key=key, defaults=fields)
    return entry


def ensure_annual_credits(user_id: int, kind: EmployeeKind, year: int) -> None:
    for policy in LeavePolicy.objects.all():
        category = Category(policy.category)
        amount = annual_credit(category, kind, policy.annual_days)
        if amount > 0:
            post(user_id, category, year, amount, Reason.ANNUAL_CREDIT,
                 key=f"credit:{category}:{year}:{user_id}")


def available(user_id: int, category: Category, year: int) -> Decimal:
    return reads.balances(user_id, year)[category] - reads.held(user_id, year)[category]


def require_available(user_id: int, category: Category, year: int, days: Decimal) -> None:
    left = available(user_id, category, year)
    if days > left:
        raise ConflictError(
            f"You have {left} day(s) of {LABELS[category]} available for {year}, "
            f"and this needs {days}.", code="insufficient_balance")
