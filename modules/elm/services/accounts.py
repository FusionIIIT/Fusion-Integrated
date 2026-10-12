"""Leave balances and the ledger that explains them, plus year-end processing."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from modules.elm.domain import enums as e
from modules.elm.domain.year_end import compute as compute_year_end
from modules.elm.models import LeaveAccount, LeaveTransaction
from modules.elm.services import config

ZERO = Decimal("0")


def ensure_account(user_id: int, category: str, year: int) -> LeaveAccount:
    """The account, credited with the category entitlement on first creation."""
    account, created = LeaveAccount.objects.get_or_create(
        user_id=user_id, category=category, year=year)
    if created:
        entitlement = config.type_config(category).annual_entitlement
        if entitlement:
            _post(account, e.LEDGER_CREDIT, entitlement, "Annual credit")
    return account


def _post(account: LeaveAccount, kind: str, amount: Decimal, note: str = "",
          request=None, actor_user_id: int | None = None) -> LeaveAccount:
    amount = Decimal(amount)
    account.balance = account.balance + amount
    fields = ["balance", "updated_at"]
    if kind == e.LEDGER_DEDUCT:
        account.used = account.used + (-amount)
        fields.append("used")
    if kind == e.LEDGER_LAPSE:
        account.lapsed = account.lapsed + (-amount)
        fields.append("lapsed")
    account.save(update_fields=fields)
    LeaveTransaction.objects.create(
        account=account, kind=kind, amount=amount,
        balance_after=account.balance, note=note, request=request,
        actor_user_id=actor_user_id)
    return account


def available(user_id: int, category: str, year: int) -> Decimal:
    return ensure_account(user_id, category, year).balance


def deduct(*, account: LeaveAccount, days: Decimal, request=None,
           actor_user_id: int | None = None, note: str = "") -> LeaveAccount:
    return _post(account, e.LEDGER_DEDUCT, -Decimal(days),
                 note or "Leave approved", request, actor_user_id)


def restore(*, account: LeaveAccount, days: Decimal, request=None,
            actor_user_id: int | None = None, note: str = "") -> LeaveAccount:
    return _post(account, e.LEDGER_RESTORE, Decimal(days),
                 note or "Leave cancelled", request, actor_user_id)


def adjust(*, account: LeaveAccount, days: Decimal, request=None,
           actor_user_id: int | None = None, note: str = "") -> LeaveAccount:
    return _post(account, e.LEDGER_ADJUST, Decimal(days), note, request,
                 actor_user_id)


def accounts_for(user_id: int, year: int) -> dict[str, LeaveAccount]:
    return {a.category: a for a in
            LeaveAccount.objects.filter(user_id=user_id, year=year)}


def transactions_for(user_id: int, year: int):
    return LeaveTransaction.objects.filter(account__user_id=user_id,
                                           account__year=year)


@transaction.atomic
def year_end(year: int, *, actor_user_id: int | None = None) -> dict:
    """Apply year-end rules to every account for `year` (EL-UC-020).

    CL/RH/SCL lapse; EL/COL carry forward; faculty VL converts to EL at 2:1.
    """
    report = {"lapsed": 0, "carried": 0, "converted": 0, "accounts": 0}
    for account in LeaveAccount.objects.filter(year=year).select_related():
        outcome = compute_year_end(category=account.category,
                                   balance=account.balance)
        report["accounts"] += 1
        if outcome.lapsed:
            _post(account, e.LEDGER_LAPSE, -outcome.lapsed,
                  f"Year-end lapse {year}", actor_user_id=actor_user_id)
            report["lapsed"] += 1
        if outcome.carried:
            nxt = ensure_account(account.user_id, account.category, year + 1)
            _post(account, e.LEDGER_CARRY, -outcome.carried,
                  f"Carried forward to {year + 1}", actor_user_id=actor_user_id)
            _post(nxt, e.LEDGER_CARRY, outcome.carried,
                  f"Carried forward from {year}", actor_user_id=actor_user_id)
            report["carried"] += 1
        if outcome.converted_to_el:
            # Drop the whole unused VL, credit half as EL next year.
            _post(account, e.LEDGER_CONVERT_OUT, -account.balance,
                  f"VL converted to EL at year end {year}",
                  actor_user_id=actor_user_id)
            el = ensure_account(account.user_id, e.EL, year + 1)
            _post(el, e.LEDGER_CONVERT_IN, outcome.converted_to_el,
                  f"EL credited from VL conversion {year}",
                  actor_user_id=actor_user_id)
            report["converted"] += 1
    return report
