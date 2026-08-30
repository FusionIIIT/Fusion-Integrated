"""Whether a requested period collides with leave the person already holds.

BR-EL-012. Two half-day CL on one date are not a collision when they occupy
different halves, which is the only case where a date can be shared.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from modules.leave.domain.counting import Half


@dataclass(frozen=True)
class Period:
    start: date
    end: date
    half: Half | None = None

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError("period cannot end before it starts")
        if self.half is not None and self.start != self.end:
            raise ValueError("a half day must be a single date")

    def touches(self, other: Period) -> bool:
        return self.start <= other.end and other.start <= self.end


def overlaps(a: Period, b: Period) -> bool:
    if not a.touches(b):
        return False
    if a.half is not None and b.half is not None:
        return a.half is b.half
    return True


def first_conflict(candidate: Period, existing: list[Period]) -> Period | None:
    """The earliest period the candidate collides with, or None."""
    hits = [p for p in existing if overlaps(candidate, p)]
    return min(hits, key=lambda p: p.start) if hits else None
