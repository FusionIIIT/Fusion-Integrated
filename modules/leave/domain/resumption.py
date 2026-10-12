"""Normal, early and late resumption (BR-EL-027, BR-EL-028).

Formal resumption review applies to EL, COL and VL (BR-EL-027). The outcome is
a comparison of the actual resumption date with the approved end date: equal
means no adjustment; earlier or later means the actual leave period is recorded
and the balance (and related records) are synchronized accordingly (BR-EL-028).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from modules.leave.domain.entitlement import COL, EL, VL

#: BR-EL-027 - categories whose return triggers a resumption review.
REVIEW_CATEGORIES: frozenset[str] = frozenset({EL, COL, VL})


class ResumptionKind(StrEnum):
    """BR-EL-028 - the three outcomes of comparing actual against approved."""

    NORMAL = "normal"
    EARLY = "early"
    LATE = "late"


def review_applies(category: str) -> bool:
    """BR-EL-027 - whether returning from this category needs a review."""
    return category in REVIEW_CATEGORIES


@dataclass(frozen=True)
class Resumption:
    kind: ResumptionKind
    #: Days of difference: negative when early, positive when late, zero when normal.
    delta_days: int

    @property
    def adjusts(self) -> bool:
        """BR-EL-028 - early and late resumptions adjust the record; normal does not."""
        return self.kind is not ResumptionKind.NORMAL


def assess(*, approved_end: date, actual: date) -> Resumption:
    """BR-EL-028 - classify a resumption by comparing dates."""
    delta_days = (actual - approved_end).days
    if delta_days == 0:
        return Resumption(ResumptionKind.NORMAL, 0)
    if delta_days < 0:
        return Resumption(ResumptionKind.EARLY, delta_days)
    return Resumption(ResumptionKind.LATE, delta_days)
