"""Overlap between two leave intervals (BR-EL-012, BR-EL-014)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Interval:
    start: date
    end: date
    half: str | None = None


def overlaps(a: Interval, b: Interval) -> bool:
    if a.end < b.start or b.end < a.start:
        return False
    return not (a.half and b.half and a.start == b.start and a.half != b.half)
