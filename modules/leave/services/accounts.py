"""Leave-account movements (BR-EL-002..009).

Two objects move together and must never diverge: the materialised
`LeaveBalance` the screens read, and the append-only `LeaveLedgerEntry` that is
the authority for why the balance is what it is. Both are written inside the
caller's transaction, and nothing here edits a ledger row — a correction is a
new entry, which is what makes a disputed balance explainable.
"""
from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction

from core.api.exceptions import ConflictError
from modules.leave.domain import categories as cat
from modules.leave.models import LeaveBalance, LeaveLedgerEntry

log = logging.getLogger("fusion.leave.accounts")

ZERO = Decimal("0")


def entitlement_for(category: str, employee_kind: str, *,
                    entitlements: dict | None = None) -> Decimal:
    """The annual credit for this category and employee kind.

    A category that does not apply to the kind is credited zero rather than its
    headline entitlement: a staff member has no VL, and creating the account
    with 60 VL would make an ineligible request look affordable.
    """
    table = entitlements or {k: str(v) for k, v in cat.ENTITLEMENT.items()}
    if not cat.may_be_used_by(category, employee_kind):
        return ZERO
    return Decimal(str(table.get(category, cat.ENTITLEMENT.get(category, 0))))


def ensure_balance(*, user_id: int, category: str, leave_year: int,
                   entitled_days: Decimal) -> LeaveBalance:
    """The account for this person, category and year, opened if necessary."""
    balance, created = LeaveBalance.objects.get_or_create(
        user_id=user_id, category=category, leave_year=leave_year,
        defaults={"entitled_days": entitled_days})
    if created and entitled_days:
        _entry(user_id=user_id, category=category, leave_year=leave_year,
               entry_type="credit", days=entitled_days,
               note=f"Annual entitlement for {leave_year}")
    return balance


def available_days(*, user_id: int, category: str, leave_year: int,
                   employee_kind: str, entitlements: dict | None = None) -> Decimal:
    """What the employee can still use, opening the account at zero if absent.

    Read-only: a validation pass must not create accounts for every category an
    employee might one day ask about.
    """
    row = LeaveBalance.objects.filter(user_id=user_id, category=category,
                                      leave_year=leave_year).first()
    if row is not None:
        return row.available_days
    return entitlement_for(category, employee_kind, entitlements=entitlements)


def _entry(*, user_id: int, category: str, leave_year: int, entry_type: str,
           days: Decimal, note: str = "", request_id: int | None = None,
           actor_user_id: int | None = None) -> None:
    LeaveLedgerEntry.objects.create(
        user_id=user_id, category=category, leave_year=leave_year,
        entry_type=entry_type, days=days, note=note[:300],
        request_id=request_id, actor_user_id=actor_user_id)


@transaction.atomic
def debit(*, user_id: int, category: str, leave_year: int, days: Decimal,
          request_id: int | None = None, entitled_days: Decimal = ZERO,
          note: str = "") -> LeaveBalance:
    """Charge leave to the account. Called on final approval."""
    if days <= 0:
        raise ConflictError("A leave posting must be a positive number of days.",
                            code="invalid_posting")
    balance = ensure_balance(user_id=user_id, category=category,
                             leave_year=leave_year, entitled_days=entitled_days)
    locked = LeaveBalance.objects.select_for_update().get(pk=balance.pk)
    if locked.available_days < days:
        raise ConflictError(
            f"Only {locked.available_days} {cat.LABELS[category]} day(s) remain; "
            f"{days} cannot be posted.", code="insufficient_balance")
    locked.used_days = locked.used_days + days
    locked.save(update_fields=["used_days", "updated_at"])
    _entry(user_id=user_id, category=category, leave_year=leave_year,
           entry_type="debit", days=days, request_id=request_id,
           note=note or "Leave posted on final approval")
    return locked


@transaction.atomic
def restore(*, user_id: int, category: str, leave_year: int, days: Decimal,
            request_id: int | None = None, note: str = "") -> LeaveBalance:
    """Give back leave that was already deducted — a cancellation, or an early
    resumption (BR-EL-023, BR-EL-028)."""
    balance = LeaveBalance.objects.select_for_update().filter(
        user_id=user_id, category=category, leave_year=leave_year).first()
    if balance is None:
        raise ConflictError(
            "There is no leave account to restore into.", code="no_account")
    balance.used_days = max(ZERO, balance.used_days - days)
    balance.save(update_fields=["used_days", "updated_at"])
    _entry(user_id=user_id, category=category, leave_year=leave_year,
           entry_type="restore", days=days, request_id=request_id,
           note=note or "Balance restored")
    return balance


@transaction.atomic
def adjust(*, user_id: int, category: str, leave_year: int, days: Decimal,
           employee_kind: str, entitlements: dict | None = None,
           note: str, actor_user_id: int, request_id: int | None = None
           ) -> LeaveBalance:
    """An administrative correction (EL-UC-017): a record change, not a decision.

    A negative `days` reduces the balance, a positive one increases it, and the
    reason is required because BR-EL-037 keeps maintenance and sanctioning
    distinguishable in the audit trail.
    """
    if days == 0:
        raise ConflictError("An adjustment of zero days does nothing.",
                            code="no_change")
    if not (note or "").strip():
        raise ConflictError("An adjustment needs a reason.", code="reason_required")
    balance = ensure_balance(
        user_id=user_id, category=category, leave_year=leave_year,
        entitled_days=entitlement_for(category, employee_kind,
                                      entitlements=entitlements))
    if days > 0:
        balance.entitled_days = balance.entitled_days + days
        fields = ["entitled_days", "updated_at"]
    else:
        balance.used_days = max(ZERO, balance.used_days + abs(days))
        fields = ["used_days", "updated_at"]
    balance.save(update_fields=fields)
    _entry(user_id=user_id, category=category, leave_year=leave_year,
           entry_type="adjust", days=abs(days), request_id=request_id,
           actor_user_id=actor_user_id, note=note)
    return balance
