"""Credits, deductions and restorations. Every change leaves a ledger row."""
from __future__ import annotations

from decimal import Decimal

from modules.elm.domain import balances as rules
from modules.elm.domain import leave_types as lt
from modules.elm.models import LeaveApplication, LeaveBalance, LeaveTransaction
from modules.elm.selectors import applications as sel


def ensure_balances(user_id: int, year: int, kind: str) -> list[LeaveBalance]:
    """The yearly credit for this kind of employee (BR-EL-002..009). Idempotent."""
    rows = []
    for leave_type, credit in lt.credit_for(kind).items():
        row, _ = LeaveBalance.objects.get_or_create(
            user_id=user_id, year=year, leave_type=leave_type,
            defaults={"entitled": credit})
        rows.append(row)
    return rows


def available(user_id: int, year: int, leave_type: str,
              exclude_id: int | None = None) -> Decimal:
    """What a new request may draw on: the balance less requests already waiting."""
    row = sel.balance(user_id, year, leave_type)
    if row is None:
        return Decimal(0)
    return row.remaining - sel.pending_days(user_id, year, leave_type, exclude_id)


def check_available(user_id: int, year: int, leave_type: str, days: Decimal,
                    exclude_id: int | None = None) -> None:
    rules.check_balance(days, available(user_id, year, leave_type, exclude_id))


def deduct(application: LeaveApplication) -> None:
    """Charge an approved leave. Re-checks under lock so two approvals cannot overdraw."""
    row = sel.balance(application.user_id, application.start_date.year,
                      application.leave_type, lock=True)
    if row is None:
        rules.check_balance(application.days, Decimal(0))
    else:
        rules.check_balance(application.days, row.remaining)
        row.used += application.days
        row.save(update_fields=["used", "updated_at"])
        LeaveTransaction.objects.create(
            balance=row, application=application, kind=LeaveTransaction.Kind.DEDUCT,
            days=application.days)


def restore(application: LeaveApplication, days: Decimal, note: str) -> None:
    """Give days back (cancellation, early resumption). Never more than was used."""
    row = sel.balance(application.user_id, application.start_date.year,
                      application.leave_type, lock=True)
    if row is None or days <= 0:
        return
    days = min(days, row.used)
    row.used -= days
    row.save(update_fields=["used", "updated_at"])
    LeaveTransaction.objects.create(
        balance=row, application=application, kind=LeaveTransaction.Kind.RESTORE,
        days=days, note=note[:200])
