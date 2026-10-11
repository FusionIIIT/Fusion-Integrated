"""Balance writes (BR-06, BR-07, BR-13). The ledger is append-only."""
from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.directory import contracts as directory
from modules.elm.models import KIND_CREDIT, KIND_GRANT, LeaveBalanceEntry, LeaveType
from modules.elm.selectors import queries
from modules.elm.services import authz

log = logging.getLogger("fusion.elm.balances")
NOTE_MAX = 300


def ensure_annual_grant(*, user_id: int, leave_type: LeaveType, year: int) -> bool:
    """Record the annual entitlement once per (person, type, year) — BR-13."""
    entitlement = leave_type.annual_entitlement_days
    if entitlement <= 0:
        return False
    _, created = LeaveBalanceEntry.objects.get_or_create(
        user_id=user_id, leave_type=leave_type, year=year, kind=KIND_GRANT,
        defaults={"days": entitlement, "note": f"Annual grant {year}"})
    return created


def grant_annual_leave(*, year: int) -> tuple[int, int]:
    """Every active employee, every effective type; idempotent by constraint.

    Batched on purpose: a per-person get_or_create is 15,000 round trips on a
    real payroll, and the unique constraint already makes a retry harmless.
    """
    employees = directory.get_employees()
    # The versions current at run time; the 1 April trigger is only the clock.
    types = [t for t in queries.types_effective_on(timezone.localdate())
             if t.annual_entitlement_days > 0]
    if not employees or not types:
        return 0, 0

    user_ids = sorted(p.user_id for p in employees)
    type_ids = [t.pk for t in types]
    existing = set(
        LeaveBalanceEntry.objects
        .filter(user_id__in=user_ids, leave_type_id__in=type_ids, year=year,
                kind=KIND_GRANT)
        .values_list("user_id", "leave_type_id"))
    rows = [
        LeaveBalanceEntry(user_id=person.user_id, leave_type=leave_type,
                          year=year, kind=KIND_GRANT,
                          days=leave_type.annual_entitlement_days,
                          note=f"Annual grant {year}")
        for person in employees
        for leave_type in types
        if (person.user_id, leave_type.pk) not in existing
    ]
    if rows:
        with transaction.atomic():
            LeaveBalanceEntry.objects.bulk_create(rows, ignore_conflicts=True,
                                                  batch_size=500)
    after = (LeaveBalanceEntry.objects
             .filter(user_id__in=user_ids, leave_type_id__in=type_ids, year=year,
                     kind=KIND_GRANT)
             .count())
    granted = after - len(existing)
    log.info("annual grant %s: %s recorded, %s already present",
             year, granted, after - granted)
    return granted, after - granted


def adjust_balance(*, actor, user_id: int, leave_type_id: int, year: int,
                   days, note: str) -> LeaveBalanceEntry:
    """A manual movement; a correction is a new entry, never an edit — BR-06."""
    authz.require(actor, "elm.balance.manage")
    try:
        amount = Decimal(str(days))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ConflictError("The adjustment must be a number of days.",
                            code="invalid_adjustment") from exc
    if amount == 0:
        raise ConflictError("An adjustment of zero days changes nothing.",
                            code="zero_adjustment")
    if not (note or "").strip():
        raise ConflictError("An adjustment needs a note explaining it.",
                            code="adjustment_note_required")

    people = directory.get_users([user_id])
    if user_id not in people:
        raise NotFoundError("That person is not in the directory.",
                            code="person_not_found")
    leave_type = LeaveType.objects.filter(pk=leave_type_id).first()
    if leave_type is None:
        raise NotFoundError("That leave type does not exist.",
                            code="leave_type_not_found")

    entry = LeaveBalanceEntry.objects.create(
        user_id=user_id, leave_type=leave_type, year=year, kind=KIND_CREDIT,
        days=amount, granted_by_user_id=getattr(actor, "user_id", None),
        note=note.strip()[:NOTE_MAX])
    log.info("balance adjustment u%s %s %s days by u%s",
             user_id, leave_type.code, amount, getattr(actor, "user_id", None))
    return entry
