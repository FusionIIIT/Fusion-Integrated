"""The ledger: one lock per employee, idempotent entries; balances are read in selectors."""
from __future__ import annotations

from decimal import Decimal

from django.db import IntegrityError, transaction

from modules.leave.domain import categories as cat
from modules.leave.domain import entitlement
from modules.leave.domain import policy as pol
from modules.leave.models import LeaveAccount, LeaveRequest, LedgerEntry
from modules.leave.selectors.balances import balances, pending_charges


def lock(user_id: int, *, employee_kind: str = "") -> LeaveAccount:
    """Serialise every balance-affecting write for one employee; call inside a transaction."""
    account, created = LeaveAccount.objects.get_or_create(
        user_id=user_id, defaults={"employee_kind": employee_kind})
    account = LeaveAccount.objects.select_for_update().get(pk=account.pk)
    if employee_kind and account.employee_kind != employee_kind and not created:
        account.employee_kind = employee_kind
        account.save(update_fields=["employee_kind", "updated_at"])
    return account


def post(*, user_id: int, year: int, category: str, delta: Decimal, entry_type: str, key: str,
         request: LeaveRequest | None = None, note: str = "",
         actor_id: int | None = None) -> LedgerEntry | None:
    """One entry, or None if this exact fact was already posted."""
    if not delta:
        return None
    try:
        with transaction.atomic():
            return LedgerEntry.objects.create(
                user_id=user_id, leave_year=year, category=category, delta=delta,
                entry_type=entry_type, request=request, idempotency_key=key, note=note[:300],
                created_by_user_id=actor_id)
    except IntegrityError:
        if LedgerEntry.objects.filter(idempotency_key=key).exists():
            return None
        raise


def ensure_annual_credit(*, user_id: int, employee_kind: str, year: int,
                         policy: pol.Policy) -> int:
    """BR-EL-002 to 006, 009: the year's credit, once, when the account is first touched."""
    made = 0
    for code, days in entitlement.annual_credits(policy, employee_kind).items():
        if post(user_id=user_id, year=year, category=code, delta=days, entry_type="credit",
                key=f"credit:{user_id}:{year}:{code}",
                note=f"Annual {cat.LABELS[code]} entitlement for {year}") is not None:
            made += 1
    return made


def available(user_id: int, year: int, category: str, *,
              exclude_request_id: int | None = None) -> Decimal:
    held = balances([user_id], year)[user_id][category]
    asked = pending_charges([user_id], year,
                            exclude_request_id=exclude_request_id)[user_id][category]
    return held - asked


__all__ = ["available", "balances", "ensure_annual_credit", "lock", "pending_charges", "post"]
