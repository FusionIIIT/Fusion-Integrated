"""Year-end leave processing (EL-UC-020).

One run per leave year, at the configured boundary.
For every account in the closing year:

* **CL / RH / SCL** — unused days lapse (PS §3).
* **VL (faculty)** — unused days convert to EL at
  the configured 2:1 ratio, fractional part
  preserved; VL itself does not carry forward.
* **EL / COL** — unused days carry forward to the
  next year's opening balance.

Every movement posts to the append-only ledger, the
next year's accounts are opened with fresh
entitlements, and anything that could not be
processed consistently is collected into the run's
exceptions report rather than failing the batch.
"""
from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction

from core.api.exceptions import ConflictError
from modules.elm.domain.leave_types import EL
from modules.elm.domain.policy import (
    vl_to_el_conversion,
    year_end_outcome,
)
from modules.elm.models import LeaveAccount, YearEndRun
from modules.elm.services import authz
from modules.elm.services import policy as policy_service

log = logging.getLogger("fusion.elm.year_end")

ZERO = Decimal("0")

#: System actor for ledger entries posted by the
#: year-end run itself.
SYSTEM_ACTOR = 0


@transaction.atomic
def run_year_end(principal, *,
                   leave_year: str) -> YearEndRun:
    """Process the year-end boundary for one leave
    year. Exactly once per year."""
    authz.require_permission(principal, "elm.yearend.run")
    if YearEndRun.objects.filter(
            leave_year=leave_year).exists():
        raise ConflictError(
            f"Year-end processing already ran for "
            f"leave year {leave_year}.",
            code="already_processed")

    stats = {"accounts": 0, "lapsed": 0,
             "converted": 0, "carried": 0,
             "days_lapsed": str(ZERO),
             "days_converted": str(ZERO),
             "days_carried": str(ZERO)}
    exceptions: list[dict] = []

    next_year = policy_service.next_leave_year(
        leave_year)
    for account in LeaveAccount.objects.filter(
            leave_year=leave_year):
        stats["accounts"] += 1
        try:
            _process_account(
                account, leave_year, next_year, stats)
        except Exception as exc:
            # One bad account must not abort the
            # run; it is reported instead.
            log.exception(
                "year-end failed for user %s %s %s",
                account.user_id, leave_year,
                account.category)
            exceptions.append({
                "user_id": account.user_id,
                "leave_year": leave_year,
                "category": account.category,
                "error": f"{type(exc).__name__}: {exc}",
            })

    run = YearEndRun.objects.create(
        leave_year=leave_year,
        processed_by_user_id=principal.user_id,
        stats=stats, exceptions=exceptions)
    log.info("year-end %s complete: %s", leave_year,
             stats)
    return run


def _process_account(account: LeaveAccount,
                       leave_year: str,
                       next_year: str,
                       stats: dict) -> None:
    profile = authz.employee_profile(account.user_id)
    employee_kind = (profile.employee_kind
                     if profile is not None
                     else "staff")
    unused = (account.opening_days
              + account.entitled_days
              - account.used_days)
    if unused < ZERO:
        raise ValueError(
            f"negative balance {unused} on "
            f"{account.category}")

    outcome = year_end_outcome(
        account.category, employee_kind, unused)

    # Open next year's account with the fresh
    # entitlement.
    next_account, _ = LeaveAccount.objects.get_or_create(
        user_id=account.user_id,
        leave_year=next_year,
        category=account.category)
    next_account.entitled_days = (
        policy_service.entitlement_for(
            account.category, employee_kind))

    if outcome == "lapse":
        if unused > ZERO:
            _ledger(account, delta=-unused,
                      kind="year_end_lapse",
                      reason=(f"Year-end lapse of "
                              f"unused {account.category} "
                              f"({leave_year})"))
            account.opening_days = ZERO
            account.entitled_days = ZERO
            account.save()
            stats["lapsed"] += 1
            stats["days_lapsed"] = str(
                Decimal(stats["days_lapsed"]) + unused)
        next_account.save()

    elif outcome == "convert":
        # Faculty VL -> EL at 2:1, fractional kept.
        converted = (vl_to_el_conversion(
            unused) if unused > ZERO else ZERO)
        if unused > ZERO:
            _ledger(account, delta=-unused,
                      kind="vl_conversion",
                      reason=(f"Year-end conversion of "
                              f"unused VL to EL "
                              f"({leave_year})"))
            account.opening_days = ZERO
            account.entitled_days = ZERO
            account.save()
        if converted > ZERO:
            el_account, _ = (
                LeaveAccount.objects.get_or_create(
                    user_id=account.user_id,
                    leave_year=next_year,
                    category=EL))
            el_account.opening_days += converted
            el_account.save()
            _ledger(el_account, delta=converted,
                      kind="vl_conversion",
                      reason=(f"VL converted to EL at "
                              f"year-end ({leave_year})"))
            stats["converted"] += 1
            stats["days_converted"] = str(
                Decimal(stats["days_converted"])
                + converted)
        else:
            stats["converted"] += 1
        next_account.save()

    else:  # carry_forward — EL, COL
        if unused > ZERO:
            next_account.opening_days = unused
            _ledger(next_account, delta=unused,
                      kind="year_end_carry_forward",
                      reason=(f"Carried forward from "
                              f"{leave_year}"))
            stats["carried"] += 1
            stats["days_carried"] = str(
                Decimal(stats["days_carried"]) + unused)
        next_account.save()


def _ledger(account: LeaveAccount, *, delta: Decimal,
              kind: str, reason: str):
    balance_after = (account.opening_days
                     + account.entitled_days
                     - account.used_days)
    return account.transactions.create(
        delta=delta, balance_after=balance_after,
        kind=kind, reason=reason,
        actor_user_id=SYSTEM_ACTOR)
