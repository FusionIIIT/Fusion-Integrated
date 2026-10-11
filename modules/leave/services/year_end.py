"""Year-end processing (EL-UC-020, BR-EL-002..009).

EVT-01 is an event trigger, not an actor: when the configured boundary is
reached the system applies each category's outcome, records the resulting
account transactions, and *reports* an exception rather than silently applying
an uncertain result. That last clause is why this service can complete with
exceptions instead of failing outright.

The run is idempotent per leave year — one `YearEndRun` row per year, so a
second execution on the same boundary cannot lapse the same days twice.
"""
from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.leave.domain import categories as cat
from modules.leave.domain import year_end as rules
from modules.leave.models import (
    LeaveBalance,
    LeaveLedgerEntry,
    LeavePolicy,
    YearEndException,
    YearEndRun,
)
from modules.leave.selectors import leave as sel

log = logging.getLogger("fusion.leave.year_end")


def boundary_for(leave_year: int) -> tuple[int, int]:
    """The configured year-end month and day (BR-EL-038's sibling, EVT-01)."""
    policy = LeavePolicy.objects.filter(leave_year=leave_year).first() \
        or LeavePolicy.objects.filter(is_current=True).first()
    if policy is None:
        return (12, 31)
    return (policy.year_end_month, policy.year_end_day)


@transaction.atomic
def run(*, leave_year: int) -> YearEndRun:
    """Apply the year-end outcomes for `leave_year` and open the next year."""
    existing = YearEndRun.objects.filter(leave_year=leave_year).first()
    if existing is not None:
        raise ConflictError(
            f"Year-end processing for {leave_year} has already run.",
            code="year_end_already_run",
            details=[{"run_id": existing.pk, "status": existing.status}])

    policy = LeavePolicy.objects.filter(leave_year=leave_year).first() \
        or LeavePolicy.objects.filter(is_current=True).first()
    ratio = policy.vl_to_el_ratio if policy else cat.VL_TO_EL_RATIO
    run_row = YearEndRun.objects.create(leave_year=leave_year, status="running")

    processed = 0
    accounts = (LeaveBalance.objects.filter(leave_year=leave_year)
                .order_by("user_id", "category"))
    for account in accounts:
        try:
            _apply(run=run_row, account=account, ratio=ratio)
        except Exception as exc:                      # noqa: BLE001 — report it
            YearEndException.objects.create(
                run=run_row, user_id=account.user_id, category=account.category,
                reason=str(exc)[:300])
            log.warning("leave.year_end.exception user=%s category=%s err=%s",
                        account.user_id, account.category, exc)
        else:
            processed += 1

    exceptions = run_row.exceptions.count()
    run_row.accounts_processed = processed
    run_row.status = "completed_with_exceptions" if exceptions else "completed"
    run_row.finished_at = timezone.now()
    run_row.note = (f"{processed} account(s) processed, {exceptions} exception(s) "
                    f"reported")
    run_row.save(update_fields=["accounts_processed", "status", "finished_at",
                                "note", "updated_at"])
    log.info("leave.year_end.completed year=%s processed=%d exceptions=%d",
             leave_year, processed, exceptions)
    return run_row


def _apply(*, run: YearEndRun, account: LeaveBalance, ratio: Decimal) -> None:
    """One account: lapse, carry forward or convert, then record it."""
    outcome = rules.outcome_for(account.category, account.available_days,
                                vl_to_el_ratio=ratio)
    if outcome.is_noop:
        return

    if outcome.action == rules.LAPSE:
        account.lapsed_days = account.lapsed_days + outcome.days_in
        account.entitled_days = Decimal("0")
        account.carried_days = Decimal("0")
        account.used_days = Decimal("0")
        account.save(update_fields=["lapsed_days", "entitled_days", "carried_days",
                                    "used_days", "updated_at"])
        _record(account=account, entry_type="lapse", days=outcome.days_in,
                note=f"Unused {account.category.upper()} lapsed at year end")

    elif outcome.action == rules.CARRY_FORWARD:
        carried = outcome.days_out
        account.used_days = Decimal("0")
        account.entitled_days = Decimal("0")
        account.carried_days = carried
        account.save(update_fields=["used_days", "entitled_days", "carried_days",
                                    "updated_at"])
        _record(account=account, entry_type="carry_forward", days=carried,
                note=f"Unused {account.category.upper()} carried forward")
        _open_next_year(account=account, opening=carried)


    elif outcome.action == rules.CONVERT:
        # BR-EL-007/008: no VL survives as VL; the EL it becomes is usable.
        account.used_days = Decimal("0")
        account.entitled_days = Decimal("0")
        account.carried_days = Decimal("0")
        account.lapsed_days = account.lapsed_days + outcome.days_in
        account.save(update_fields=["used_days", "entitled_days", "carried_days",
                                    "lapsed_days", "updated_at"])
        _record(account=account, entry_type="convert", days=outcome.days_in,
                note=f"Converted {outcome.days_in} VL to {outcome.days_out} EL")
        _open_next_year(account=account, opening=Decimal("0"))
        target = (LeaveBalance.objects
                  .select_for_update()
                  .filter(user_id=account.user_id, category=cat.EL,
                          leave_year=account.leave_year + 1).first())
        if target is None:
            raise RuntimeError("the EL account the conversion credits is missing")
        target.carried_days = target.carried_days + outcome.days_out
        target.save(update_fields=["carried_days", "updated_at"])
        LeaveLedgerEntry.objects.create(
            user_id=account.user_id, category=cat.EL,
            leave_year=account.leave_year + 1, entry_type="convert",
            days=outcome.days_out,
            note=f"EL created from {outcome.days_in} unused VL at year end")
    else:                                     # pragma: no cover — model guard
        raise RuntimeError(
            f"no year-end outcome is defined for {account.category!r}")


def _record(*, account: LeaveBalance, entry_type: str, days: Decimal,
            note: str) -> None:
    LeaveLedgerEntry.objects.create(
        user_id=account.user_id, category=account.category,
        leave_year=account.leave_year, entry_type=entry_type, days=days,
        note=note[:300])


def _open_next_year(*, account: LeaveBalance, opening: Decimal) -> LeaveBalance:
    """Create the next year's account so a carry-forward has somewhere to land.

    The year-end run is unique per leave year, so this adds the opening balance
    rather than assuming a fresh row: an account opened earlier in the new year
    (by an approved request) must not lose the carry-forward.
    """
    next_year = account.leave_year + 1
    policy = sel.current_policy(next_year)
    entitlement = Decimal("0")
    if policy:
        entitlement = Decimal(str(policy.entitlements.get(account.category, 0)))
    row, _created = LeaveBalance.objects.get_or_create(
        user_id=account.user_id, category=account.category, leave_year=next_year,
        defaults={"entitled_days": entitlement})
    if opening:
        row.carried_days = row.carried_days + opening
        row.save(update_fields=["carried_days", "updated_at"])
    return row
