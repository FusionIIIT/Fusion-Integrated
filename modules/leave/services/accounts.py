"""Opening accounts and posting ledger movements.

Balances are projections of the ledger, so every movement goes through `post`.
Opening a year is idempotent: each movement carries a reference of
`year:YYYY`, and a second call for the same year finds it and does nothing.
"""
from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction

from modules.leave.domain import categories as cat
from modules.leave.domain import ledger as led
from modules.leave.domain import yearend
from modules.leave.models import LeaveAccount, LeaveLedgerEntry
from modules.leave.selectors import config as config_selector

log = logging.getLogger("fusion.leave.accounts")

ZERO = Decimal("0")


def ensure_account(*, user_id: int, year: int, category: str) -> LeaveAccount:
    row, _ = LeaveAccount.objects.get_or_create(user_id=user_id, year=year,
                                                category=category)
    return row


def post(*, account: LeaveAccount, entry_type: str, days, reference: str = "",
         reason: str = "", actor_user_id: int | None = None) -> LeaveLedgerEntry:
    """Append one movement. `days` is a magnitude; the sign comes from the type."""
    return LeaveLedgerEntry.objects.create(
        account=account, entry_type=entry_type,
        days=Decimal(str(days)).quantize(Decimal("0.01")),
        reference=reference, reason=reason, actor_user_id=actor_user_id,
    )


def closing_balance(*, user_id: int, year: int, category: str) -> Decimal:
    account = LeaveAccount.objects.filter(user_id=user_id, year=year,
                                          category=category).first()
    if account is None:
        return ZERO
    return led.project(account.entries.values_list("entry_type", "days")
                       .order_by("id"))


def converted_from_vl(*, user_id: int, year: int) -> Decimal:
    """What a faculty member's VL turned into at that year end (BR-EL-007)."""
    account = LeaveAccount.objects.filter(user_id=user_id, year=year,
                                          category=cat.VL).first()
    if account is None:
        return ZERO
    rows = account.entries.filter(entry_type=led.CONVERSION_IN) \
        .values_list("days", flat=True)
    return sum((Decimal(str(d)) for d in rows), ZERO)


def open_year(*, user_id: int, year: int, is_faculty: bool,
              actor_user_id: int | None = None) -> dict[str, LeaveAccount]:
    """Make sure this person has this year's accounts, credited exactly once."""
    accounts: dict[str, LeaveAccount] = {}
    for category in cat.CATEGORIES:
        if not cat.applicable_to(category, is_faculty=is_faculty):
            continue
        account = ensure_account(user_id=user_id, year=year, category=category)
        accounts[category] = account
        _open_one(account=account, year=year, actor_user_id=actor_user_id)
    return accounts


def _open_one(*, account: LeaveAccount, year: int,
              actor_user_id: int | None) -> None:
    reference = f"year:{year}"
    if account.entries.filter(reference=reference).exists():
        return

    opening = _carried_in(user_id=account.user_id, year=year,
                          category=account.category)
    if opening:
        led_reason = "Carried forward from the previous year"
        post(account=account, entry_type=led.OPENING, days=opening,
             reference=reference, reason=led_reason, actor_user_id=actor_user_id)

    credit = Decimal(config_selector.entitlement(account.category))
    if credit:
        post(account=account, entry_type=led.ACCRUAL, days=credit,
             reference=reference,
             reason=f"{year} entitlement for {cat.LABELS[account.category]}",
             actor_user_id=actor_user_id)


def _carried_in(*, user_id: int, year: int, category: str) -> Decimal:
    """What last year leaves for this category (BR-EL-005, BR-EL-007, BR-EL-008)."""
    if category == cat.EL:
        # EL carries itself, and the EL created by an unused VL also lands here.
        balance = closing_balance(user_id=user_id, year=year - 1, category=cat.EL)
        return max(balance, ZERO) + converted_from_vl(user_id=user_id, year=year - 1)
    if category in cat.CARRY_FORWARD:
        return max(closing_balance(user_id=user_id, year=year - 1,
                                   category=category), ZERO)
    return ZERO


@transaction.atomic
def debit_for_approval(*, request, days, actor_user_id: int | None = None
                       ) -> LeaveLedgerEntry:
    """Post the approved days (BR-EL-005, BR-EL-009)."""
    account = ensure_account(user_id=request.user_id,
                             year=request.start_date.year,
                             category=request.category)
    return post(account=account, entry_type=led.DEBIT, days=days,
                reference=f"request:{request.pk}",
                reason=f"{cat.LABELS[request.category]} from "
                       f"{request.start_date} to {request.end_date}",
                actor_user_id=actor_user_id)


@transaction.atomic
def restore_for_cancellation(*, request, days, actor_user_id: int | None = None
                             ) -> LeaveLedgerEntry:
    """BR-EL-023: an approved cancellation restores the deducted balance."""
    account = ensure_account(user_id=request.user_id,
                             year=request.start_date.year,
                             category=request.category)
    return post(account=account, entry_type=led.CREDIT, days=days,
                reference=f"cancelled:{request.pk}",
                reason=f"Cancellation of the leave from {request.start_date}",
                actor_user_id=actor_user_id)


def settle_year(*, year: int, actor_user_id: int | None = None) -> dict:
    """Year end for every account of a year (BR-EL-002..009, EL-UC-020)."""
    report = {"accounts": 0, "lapsed": ZERO, "carried": ZERO, "converted_el": ZERO,
              "exceptions": []}
    accounts = LeaveAccount.objects.filter(year=year).order_by("user_id", "category")
    for account in accounts:
        closing = led.project(account.entries.values_list("entry_type", "days")
                              .order_by("id"))
        outcome = yearend.settle(category=account.category, closing=closing)
        try:
            with transaction.atomic():
                _write_outcome(account=account, outcome=outcome,
                               actor_user_id=actor_user_id)
        except Exception as exc:                              # noqa: BLE001
            # EL-UC-020: report the exception rather than commit a guess.
            log.warning("leave.yearend.exception account=%s err=%s", account.pk, exc)
            report["exceptions"].append({"account": account.pk, "error": str(exc)})
            continue
        report["accounts"] += 1
        report["lapsed"] += outcome.lapsed
        report["carried"] += outcome.carried_forward
        report["converted_el"] += outcome.converted_el
    log.info("leave.yearend.done year=%s accounts=%d exceptions=%d", year,
             report["accounts"], len(report["exceptions"]))
    return report


def _write_outcome(*, account: LeaveAccount, outcome: yearend.YearEndOutcome,
                   actor_user_id: int | None) -> None:
    if not outcome.moves():
        return
    reference = f"yearend:{account.year}"
    if account.entries.filter(reference=reference).exists():
        return
    for entry_type, days in outcome.moves():
        post(account=account, entry_type=entry_type, days=days, reference=reference,
             reason=f"Year-end processing for {account.year}",
             actor_user_id=actor_user_id)
