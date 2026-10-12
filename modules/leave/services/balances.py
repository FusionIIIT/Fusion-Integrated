"""Balance reads and the ledger (BR-EL-002…009, CFR-EL-003.5).

Rows are materialised so an approval can lock one with `select_for_update`
inside its own transaction; the account transaction is the immutable evidence
behind every number on the balance screen.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from modules.directory import contracts as directory
from modules.leave.domain.categories import CATEGORIES, VL
from modules.leave.models import LeaveAccountTransaction, LeaveBalance
from modules.leave.services import authz
from modules.leave.services.policy import (
    current_leave_year,
    current_policy,
    entitlement,
    is_faculty,
)

#: Which balance column each ledger kind moves. Signs live in the `days`
#: argument, so every kind has exactly one home.
FIELD_FOR_KIND = {
    LeaveAccountTransaction.CREDIT: "credited",
    LeaveAccountTransaction.DEDUCTION: "used",
    LeaveAccountTransaction.EXTENSION_DEDUCTION: "used",
    LeaveAccountTransaction.CANCELLATION_RESTORATION: "used",
    LeaveAccountTransaction.REFUND: "used",
    LeaveAccountTransaction.ADMIN_ADJUSTMENT: "adjusted",
    LeaveAccountTransaction.CARRY_FORWARD: "carried_forward",
    LeaveAccountTransaction.VL_TO_EL_CONVERSION: "adjusted",
    LeaveAccountTransaction.YEAR_END_LAPSE: "adjusted",
}


def _kind_of(user_id: int) -> str:
    users = directory.get_users([user_id])
    return users[user_id].kind if user_id in users else "staff"


def _credit_open_year(row: LeaveBalance) -> None:
    """Top `credited` up to this year's entitlement while the year is open.

    Idempotent: it only ever raises `credited` toward the entitlement, so a
    policy change applies prospectively without re-crediting conversions or
    adjustments (which live in other columns).
    """
    policy = current_policy()
    if row.year > current_leave_year(policy):
        return
    faculty = is_faculty(_kind_of(row.user_id))
    entitled = entitlement(policy, row.category, faculty)
    if row.credited < entitled:
        row.credited = entitled
        row.save(update_fields=["credited", "updated_at"])


def ensure_year(user_id: int, year: int, *, kind: str | None = None,
                credit: bool = True) -> dict[str, LeaveBalance]:
    """Materialise every applicable category row for this year.

    Staff get no VL track (BR-EL-006); everyone else gets all six so the
    balance screen shows zeroes rather than holes. `credit=False` materialises
    without topping up to entitlement — the year-end sweep processes the
    balances as they stand and must not invent a year's credit on the way out.
    """
    faculty = is_faculty(kind if kind is not None else _kind_of(user_id))
    rows: dict[str, LeaveBalance] = {}
    for category in CATEGORIES:
        if category == VL and not faculty:
            continue
        row, _ = LeaveBalance.objects.get_or_create(
            user_id=user_id, category=category, year=year)
        if credit:
            _credit_open_year(row)
        rows[category] = row
    return rows


def available(user_id: int, category: str, year: int,
              *, kind: str | None = None) -> Decimal:
    rows = ensure_year(user_id, year, kind=kind)
    row = rows.get(category)
    if row is None:
        return Decimal(0)
    return row.carried_forward + row.credited + row.adjusted - row.used


@transaction.atomic
def post(user_id: int, category: str, year: int, kind: str, days: Decimal,
         *, request=None, note: str = "",
         actor_user_id: int | None = None,
         credit: bool = True) -> LeaveAccountTransaction:
    """One ledger entry under a row lock: the balance moves and the evidence
    is written in the same transaction, or neither happens.

    `credit=False` skips the entitlement top-up — the year-end sweep posts
    against balances as they stand, and topping up mid-sweep would grant a
    year's credit on the way out of it."""
    row, _ = (LeaveBalance.objects.select_for_update()
              .get_or_create(user_id=user_id, category=category, year=year))
    if credit:
        _credit_open_year(row)
    field = FIELD_FOR_KIND[kind]
    setattr(row, field, getattr(row, field) + Decimal(days))
    row.save(update_fields=[field, "updated_at"])
    return LeaveAccountTransaction.objects.create(
        user_id=user_id, category=category, year=year, kind=kind,
        days=Decimal(days), request=request, note=note[:300],
        actor_user_id=actor_user_id)


def deduct(user_id: int, category: str, year: int, days, *, request=None,
           note: str = "", actor_user_id: int | None = None):
    """Approved leave consumes balance (positive days)."""
    return post(user_id, category, year,
                LeaveAccountTransaction.DEDUCTION, Decimal(days),
                request=request, note=note, actor_user_id=actor_user_id)


def restore(user_id: int, category: str, year: int, days, *, request=None,
            note: str = "", actor_user_id: int | None = None):
    """A cancelled or short-returned leave gives days back (negative)."""
    return post(user_id, category, year,
                LeaveAccountTransaction.CANCELLATION_RESTORATION,
                -abs(Decimal(days)), request=request, note=note,
                actor_user_id=actor_user_id)


def refund(user_id: int, category: str, year: int, days, *, request=None,
           note: str = "", actor_user_id: int | None = None):
    """Resumption review found fewer days taken than approved."""
    return post(user_id, category, year, LeaveAccountTransaction.REFUND,
                -abs(Decimal(days)), request=request, note=note,
                actor_user_id=actor_user_id)


def adjust(actor, user_id: int, category: str, year: int, days, note: str
           ) -> LeaveAccountTransaction:
    """Record maintenance, never sanctioning (BR-EL-037): audited as its own
    ledger kind so it can never masquerade as an approval."""
    authz.require(actor, "leave.balance.update")
    days = Decimal(str(days))
    if days == 0:
        from core.api.exceptions import BadRequestError
        raise BadRequestError("A zero-day adjustment changes nothing.",
                              code="zero_adjustment")
    return post(user_id, category, year,
                LeaveAccountTransaction.ADMIN_ADJUSTMENT, days,
                note=note, actor_user_id=getattr(actor, "user_id", None))
