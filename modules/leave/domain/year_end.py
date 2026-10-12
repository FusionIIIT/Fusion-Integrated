"""Year-end lapse, carry-forward and VL conversion (PS §3, BR-EL-002…009).

Pure planning: given balances and a policy, decide the ledger entries. The
service (services/yearend.py) owns persistence, locking and idempotency.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from modules.leave.domain.categories import (
    CARRY_FORWARD_CATEGORIES,
    CONVERTING_CATEGORIES,
    LAPSING_CATEGORIES,
    COL,
    EL,
)

@dataclass(frozen=True)
class LedgerEntry:
    """One balance mutation for the year-end run.

    `direction` is applied by the service: `debit` reduces the balance
    (lapse / conversion out), `credit` increases it (carry-forward into the
    new year / conversion into EL).
    """
    user_id: int
    category: str
    year: int
    kind: str
    days: Decimal
    direction: str  # "debit" | "credit"


@dataclass(frozen=True)
class YearEndPlan:
    year: int
    entries: tuple[LedgerEntry, ...]
    exceptions: tuple[str, ...]


def plan_year_end(
    *,
    year: int,
    balances: list[tuple[int, str, Decimal]],  # (user_id, category, available)
    is_faculty: dict[int, bool],
    vl_to_el_numerator: Decimal,
    vl_to_el_denominator: Decimal,
    carry_forward_enabled: dict[str, bool],
) -> YearEndPlan:
    """BR-EL-002/003/004 lapse, BR-EL-005/006 convert, BR-EL-007/008 carry.

    Idempotency is the caller's problem: this function is a pure projection
    of "balances as they stand now".
    """
    entries: list[LedgerEntry] = []
    exceptions: list[str] = []
    next_year = year + 1

    for user_id, category, available in balances:
        if available <= 0:
            continue

        if category in LAPSING_CATEGORIES:
            # BR-EL-002/003/004: CL, RH and SCL lapse outright.
            entries.append(LedgerEntry(user_id, category, year,
                                       "year_end_lapse", -available, "debit"))

        elif category in CONVERTING_CATEGORIES:
            if not is_faculty.get(user_id):
                # VL is faculty-only; a non-faculty VL balance lapses
                # rather than converts (BR-EL-006 scope).
                entries.append(LedgerEntry(user_id, category, year,
                                           "year_end_lapse", -available,
                                           "debit"))
                continue
            # BR-EL-005: at year end, 2 VL : 1 EL (policy ratio).
            el_days = (available * vl_to_el_denominator
                       / vl_to_el_numerator)
            el_days = el_days.quantize(Decimal("0.25"))
            entries.append(LedgerEntry(user_id, category, year,
                                       "vl_to_el_conversion", -available,
                                       "debit"))
            entries.append(LedgerEntry(user_id, EL, next_year,
                                       "vl_to_el_conversion", el_days,
                                       "credit"))

        elif category in CARRY_FORWARD_CATEGORIES:
            if not carry_forward_enabled.get(category, True):
                entries.append(LedgerEntry(user_id, category, year,
                                           "year_end_lapse", -available,
                                           "debit"))
                continue
            # BR-EL-007/008: EL and COL carry forward as-is. Two entries: the
            # destination year receives it, the expiring year loses it.
            entries.append(LedgerEntry(user_id, category, next_year,
                                       "carry_forward", available, "credit"))
            entries.append(LedgerEntry(user_id, category, year,
                                       "carry_forward", -available, "debit"))

        else:
            exceptions.append(
                f"{category} for user {user_id} has no year-end rule")

    return YearEndPlan(year=year, entries=tuple(entries),
                       exceptions=tuple(exceptions))
