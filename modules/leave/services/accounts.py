"""The leave account: entitlements, ledger, and what is available.

A balance is never edited directly. `post()` is the only writer, and every call
leaves a LeaveTransaction behind, so "why is my CL 3.5?" always has an answer.
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from django.db import transaction

from modules.leave.domain import categories as cat
from modules.leave.models import LeaveBalance, LeaveRequest, LeaveTransaction
from modules.leave.selectors import balances as balance_selectors

log = logging.getLogger("fusion.leave.accounts")

CREDIT = Decimal(1)
DEBIT = Decimal(-1)


def open_account(*, user_id: int, year_label: str, category: str) -> LeaveBalance:
    row, _ = LeaveBalance.objects.get_or_create(
        user_id=user_id, year_label=year_label, category=category)
    return row


def available(user_id: int, year_label: str, category: str) -> Decimal:
    return balance_selectors.balance_for(user_id, year_label, category)


@transaction.atomic
def post(*, user_id: int, year_label: str, category: str, days: Decimal,
         kind: str, note: str = "",
         request: LeaveRequest | None = None) -> LeaveTransaction:
    """Credit or consume days, and record why.

    `days` is signed by the caller's intent: a credit is positive, a deduction
    negative. `kind` comes from LeaveTransaction.KINDS, which is what makes the
    ledger readable a year later.
    """
    row = open_account(user_id=user_id, year_label=year_label, category=category)
    if days >= 0:
        row.credited += days
    else:
        row.used += -days
    row.save(update_fields=["credited", "used"])
    return LeaveTransaction.objects.create(
        user_id=user_id, year_label=year_label, category=category, kind=kind,
        days=days, request=request, note=note)


def credit_annual(*, user_id: int, year_label: str, employee_kind: str,
                  policy) -> list[LeaveTransaction]:
    """The year's entitlement (BR-EL-002..009).

    Idempotent per account: a second call on a year already credited is a
    no-op, because the annual credit is a single transaction per account and
    the check is `credited > 0 and only annual rows exist`.
    """
    written: list[LeaveTransaction] = []
    for code in cat.eligible_categories(employee_kind):
        days = cat.annual_credit(code, employee_kind)
        if not days:
            continue
        open_account(user_id=user_id, year_label=year_label, category=code)
        if LeaveTransaction.objects.filter(
                user_id=user_id, year_label=year_label, category=code,
                kind="annual_credit").exists():
            continue
        written.append(post(user_id=user_id, year_label=year_label,
                            category=code, days=Decimal(days),
                            kind="annual_credit",
                            note=f"{policy.year_label} entitlement"))
    return written


def carry_forward(*, user_id: int, from_year: str, to_year: str) -> list[LeaveTransaction]:
    """Move a carried-forward balance into the new year's account.

    Run once per employee per boundary. The opening figure of the new account
    is the sum of what actually carried, not a copy of last year's total.
    """
    written: list[LeaveTransaction] = []
    for row in LeaveBalance.objects.filter(user_id=user_id, year_label=from_year):
        amount = row.available
        if amount <= 0:
            continue
        if not cat.category(row.category).carries_forward:
            continue
        target = open_account(user_id=user_id, year_label=to_year,
                              category=row.category)
        if LeaveTransaction.objects.filter(
                user_id=user_id, year_label=to_year,
                category=row.category, kind="carry_forward").exists():
            continue
        target.opening += amount
        target.save(update_fields=["opening"])
        written.append(LeaveTransaction.objects.create(
            user_id=user_id, year_label=to_year, category=row.category,
            kind="carry_forward", days=amount,
            note=f"Carried forward from {from_year}"))
    return written


def next_year_label(year_label: str) -> str:
    """"2026-27" -> "2027-28"."""
    try:
        start, end = year_label.split("-")
        return f"{int(start) + 1}-{int(end) + 1}"
    except (ValueError, AttributeError):
        return year_label


def year_for(date_value: date, policy) -> str:
    """Which leave year a date falls in.

    The boundary is the policy's `year_end_on`, not 1 January — the institute's
    leave year is the academic one, and the year-end trigger fires on it.
    """
    if policy is None:
        return f"{date_value.year}"
    if date_value <= policy.year_end_on:
        return policy.year_label
    return next_year_label(policy.year_label)
