"""ELM vocabulary, in pure Python.

No Django import here (the import-linter contract enforces it), so every rule
in `policy.py` is testable without a database.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class LeaveCategory(StrEnum):
    """BR-EL-001: the only categories a new request may use."""

    CL = "CL"      # Casual Leave
    RH = "RH"      # Restricted Holiday
    SCL = "SCL"    # Special Casual Leave
    EL = "EL"      # Earned Leave
    COL = "COL"    # Commuted Leave
    VL = "VL"      # Vacation Leave (faculty only)


class HalfDay(StrEnum):
    """BR-EL-010: CL may be taken as the first or second half of one day."""

    NONE = ""
    FIRST = "first"
    SECOND = "second"


class LeaveStatus(StrEnum):
    PENDING = "pending"                    # waiting for the Unit Head
    RECOMMENDED = "recommended"            # higher-sanction, Unit Head said yes
    NOT_RECOMMENDED = "not_recommended"    # higher-sanction, Unit Head said no
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


#: The Unit Head is the final authority for these (BR-EL-016).
UNIT_HEAD_FINAL = frozenset({LeaveCategory.CL, LeaveCategory.RH})

#: These need a recommendation and then a higher sanction (BR-EL-017/018).
HIGHER_SANCTION = frozenset({LeaveCategory.SCL, LeaveCategory.EL,
                             LeaveCategory.COL, LeaveCategory.VL})

#: Weekends and holidays inside the interval count as leave (BR-EL-011).
CONTINUOUS = frozenset({LeaveCategory.EL, LeaveCategory.COL, LeaveCategory.VL})

#: Requests in these states still hold their dates and their days.
ACTIVE = frozenset({LeaveStatus.PENDING, LeaveStatus.RECOMMENDED,
                    LeaveStatus.NOT_RECOMMENDED, LeaveStatus.APPROVED})

TERMINAL = frozenset({LeaveStatus.APPROVED, LeaveStatus.REJECTED,
                      LeaveStatus.WITHDRAWN})


@dataclass(frozen=True)
class LeaveSpan:
    """The dates a request occupies. `half` is only meaningful for one-day CL."""

    start: date
    end: date
    half: HalfDay = HalfDay.NONE

    def overlaps(self, other: LeaveSpan) -> bool:
        """BR-EL-012: two halves of the same single day do not overlap."""
        if self.end < other.start or other.end < self.start:
            return False
        same_day = self.start == self.end == other.start == other.end
        return not (same_day and self.half and other.half
                    and self.half != other.half)


@dataclass(frozen=True)
class Balance:
    category: LeaveCategory
    credited: Decimal
    availed: Decimal
    reserved: Decimal = Decimal(0)     # days held by pending requests

    @property
    def available(self) -> Decimal:
        return self.credited - self.availed - self.reserved
