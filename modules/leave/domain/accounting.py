"""Year-end outcomes and resumption adjustments, as postings to compute."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from modules.leave.domain.categories import CARRIES_FORWARD, LAPSES, RESUMABLE, Category


class Reason(StrEnum):
    ANNUAL_CREDIT = "annual_credit"
    DEBIT = "debit"
    RESTORE = "restore"
    RESUMPTION_ADJUST = "resumption_adjust"
    LAPSE = "lapse"
    CONVERT_OUT = "convert_out"
    CONVERT_IN = "convert_in"
    CARRY_OUT = "carry_out"
    CARRY_IN = "carry_in"
    OFFLINE = "offline"
    CORRECTION = "correction"


@dataclass(frozen=True)
class Posting:
    category: Category
    year: int
    days: Decimal
    reason: Reason


def year_end_postings(year: int, remaining: dict[Category, Decimal]) -> list[Posting]:
    """BR-EL-002..009 applied to one employee's closing balances."""
    out: list[Posting] = []
    for category, left in sorted(remaining.items()):
        if left <= 0:
            continue
        if category in LAPSES:
            out.append(Posting(category, year, -left, Reason.LAPSE))
        elif category is Category.VL:
            # BR-EL-007: 2 VL : 1 EL, fractions kept; BR-EL-008: it lands as EL.
            out.append(Posting(Category.VL, year, -left, Reason.CONVERT_OUT))
            out.append(Posting(Category.EL, year + 1, left / 2, Reason.CONVERT_IN))
        elif category in CARRIES_FORWARD:
            out.append(Posting(category, year, -left, Reason.CARRY_OUT))
            out.append(Posting(category, year + 1, left, Reason.CARRY_IN))
    return out


class Outcome(StrEnum):
    NORMAL = "normal"
    EARLY = "early"
    LATE = "late"


class NotResumable(ValueError):
    pass


def resumption_outcome(category: Category, approved_end: date,
                       actual: date) -> tuple[Outcome, Decimal]:
    """BR-EL-028: the signed balance change; continuous counting applies (BR-EL-011)."""
    if category not in RESUMABLE:
        raise NotResumable("Resumption review applies to EL, COL and VL only.")
    delta = Decimal((approved_end - actual).days)
    if delta == 0:
        return Outcome.NORMAL, Decimal(0)
    return (Outcome.EARLY if delta > 0 else Outcome.LATE), delta
