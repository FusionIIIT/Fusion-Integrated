"""Year-end balance outcomes (CFR-EL-028, BR-EL-002..009).

Pure arithmetic over balances the caller supplies, so the year-end sweep is a
thin transactional wrapper and the figures are testable without a database.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from modules.leave.domain import categories as cat
from modules.leave.domain.policy import Policy


@dataclass(frozen=True)
class Outcome:
    """One ledger movement the year-end run must post."""
    category: str
    kind: str
    days: Decimal
    note: str


@dataclass(frozen=True)
class Balance:
    user_id: int
    category: str
    days: Decimal


def _convert_vacation(unused: Decimal, ratio: Decimal) -> Decimal:
    """BR-EL-007: 2 VL : 1 EL, fractions included."""
    if unused <= 0 or ratio <= 0:
        return Decimal("0")
    return (unused / ratio).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def plan(policy: Policy, kind: str, balances: list[Balance],
         year: int) -> list[Outcome]:
    """What year end does to one employee's balances.

    CL, RH and SCL lapse (BR-EL-002/003/004). Faculty VL converts to EL and
    never carries forward as VL (BR-EL-007/008). EL and COL carry forward
    (BR-EL-005/009), subject to whatever cap the policy carries.
    """
    out: list[Outcome] = []
    for balance in balances:
        unused = balance.days
        if unused <= 0:
            continue
        category = balance.category

        if category == cat.VACATION:
            if kind != cat.FACULTY:
                out.append(Outcome(category, "lapse", unused,
                                   "Vacation Leave cannot be carried forward."))
                continue
            out.append(Outcome(category, "lapse", unused,
                               "Unused Vacation Leave does not carry forward."))
            converted = _convert_vacation(unused, policy.vacation_to_earned_ratio)
            if converted > 0:
                out.append(Outcome(cat.EARNED, "conversion", converted,
                                   "Vacation Leave converted to Earned Leave."))
            continue

        if category not in cat.CARRIES_FORWARD:
            out.append(Outcome(category, "lapse", unused,
                               "Unused leave of this category lapses at year end."))
            continue

        if not policy.carries_forward(category):
            out.append(Outcome(category, "lapse", unused,
                               "Carry-forward is switched off for this category."))
            continue

        cap = policy.carry_forward_cap(category)
        carried = unused if cap is None else min(unused, cap)
        out.append(Outcome(category, "carry_forward", carried,
                           "Unused balance carried into the next year."))
        if carried < unused:
            out.append(Outcome(category, "lapse", unused - carried,
                               "Unused balance above the carry-forward cap lapses."))
    return out