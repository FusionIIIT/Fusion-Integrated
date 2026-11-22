"""Post leave movements: append to the ledger, move the projected balance.

Both happen in one transaction, with the balance row locked, so two approvals
approved at the same instant cannot both read the same figure and write two
answers (BR-EL-026). The ledger is only ever appended to; a mistake is corrected
by a reversing entry, never by editing history.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction

from modules.leave.models import LeaveBalance, LeaveLedgerEntry
from modules.leave.models.accounts import ADDITIVE, REVERSAL


class LedgerError(Exception):
    """A posting that the ledger itself refuses."""


@dataclass(frozen=True)
class Posting:
    user_id: int
    year: int
    category: str
    kind: str
    days: Decimal
    note: str = ""
    leave_request_id: int | None = None


def _locked_balance(user_id: int, year: int, category: str) -> LeaveBalance:
    row, created = LeaveBalance.objects.get_or_create(
        user_id=user_id, year=year, category=category,
        defaults={"days": Decimal("0")})
    if created:
        return row
    return LeaveBalance.objects.select_for_update().get(pk=row.pk)


@transaction.atomic
def post(postings: Iterable[Posting], *,
         created_by_user_id: int | None = None) -> list[LeaveLedgerEntry]:
    """Append each posting and move the matching balance in the same transaction."""
    written: list[LeaveLedgerEntry] = []
    for posting in postings:
        if posting.days < 0:
            raise LedgerError("Post a negative quantity as a debit kind; "
                              "day amounts are magnitudes.")
        balance = _locked_balance(posting.user_id, posting.year, posting.category)
        balance.days = (balance.days + posting.days if posting.kind in ADDITIVE
                        else balance.days - posting.days)
        entry = LeaveLedgerEntry.objects.create(
            user_id=posting.user_id, year=posting.year, category=posting.category,
            kind=posting.kind, days=posting.days, note=posting.note,
            leave_request_id=posting.leave_request_id,
            created_by_user_id=created_by_user_id)
        balance.save(update_fields=["days", "updated_at"])
        written.append(entry)
    return written


@transaction.atomic
def reverse(entry: LeaveLedgerEntry, *, note: str = "",
            created_by_user_id: int | None = None) -> LeaveLedgerEntry:
    """Undo an entry with its mirror image, leaving the original readable."""
    if entry.kind == REVERSAL:
        raise LedgerError("A reversal cannot itself be reversed; post a new entry.")
    mirror = LeaveLedgerEntry.objects.filter(reverses_id=entry.pk).first()
    if mirror is not None:
        raise LedgerError("This entry has already been reversed.")
    if entry.days == 0:
        raise LedgerError("A zero entry has nothing to reverse.")
    balance = _locked_balance(entry.user_id, entry.year, entry.category)
    if entry.kind not in ADDITIVE and balance.days < entry.days:
        raise LedgerError(
            f"Reversing {entry.days} {entry.category} would take the balance "
            f"below zero (currently {balance.days}).")
    balance.days = (balance.days - entry.days if entry.kind in ADDITIVE
                    else balance.days + entry.days)
    balance.save(update_fields=["days", "updated_at"])
    return LeaveLedgerEntry.objects.create(
        user_id=entry.user_id, year=entry.year, category=entry.category,
        kind=REVERSAL, days=entry.days, note=note or f"Reverses #{entry.pk}",
        leave_request_id=entry.leave_request_id, reverses_id=entry.pk,
        created_by_user_id=created_by_user_id)


def reconcile(user_id: int, year: int, *, category: str = "") -> list[LeaveBalance]:
    """Rebuild the projection from the ledger. For a repair command and tests."""
    rows = LeaveLedgerEntry.objects.filter(user_id=user_id, year=year)
    if category:
        rows = rows.filter(category=category)
    rebuilt: dict[str, Decimal] = {}
    for row in rows:
        rebuilt[row.category] = rebuilt.get(row.category, Decimal("0")) + row.signed_days
    with transaction.atomic():
        for cat, days in rebuilt.items():
            LeaveBalance.objects.update_or_create(
                user_id=user_id, year=year, category=cat,
                defaults={"days": days})
    return list(LeaveBalance.objects.filter(user_id=user_id, year=year))


def balance(user_id: int, year: int, category: str) -> LeaveBalance:
    return LeaveBalance.objects.get(user_id=user_id, year=year, category=category)