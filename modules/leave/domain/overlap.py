"""Interval overlap, including the half-day CL exception (BR-EL-012)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from modules.leave.domain import categories as cat


@dataclass(frozen=True)
class Interval:
    start: date
    end: date
    category: str
    half_day: bool = False
    half: str | None = None


def _overlaps(a: Interval, b: Interval) -> bool:
    return a.start <= b.end and b.start <= a.end


def _different_cl_halves(a: Interval, b: Interval) -> bool:
    """Two CL halves on one date do not overlap when they occupy different halves."""
    return (a.category == cat.CASUAL and b.category == cat.CASUAL
            and a.half_day and b.half_day
            and a.half is not None and b.half is not None
            and a.half != b.half
            and a.start == b.start and a.end == b.end)


def find_conflict(candidate: Interval,
                  existing: list[Interval]) -> Interval | None:
    """The first existing interval the candidate impermissibly overlaps, if any."""
    for other in existing:
        if _different_cl_halves(candidate, other):
            continue
        if _overlaps(candidate, other):
            return other
    return None


def split_overlaps(*, other_requests, category: str, start_date: date,
                   end_date: date, half_day: bool = False,
                   half: str = "") -> dict[str, list]:
    """BR-EL-024, grouped for the message the applicant sees: which of their other
    requests collide, and which do not because they fall in the exempt groups."""
    candidate = Interval(start_date, end_date, category, half_day, half or None)
    conflicting, exempt = [], []
    for row in other_requests:
        other = Interval(row.start_date, row.end_date, row.category,
                         row.half_day, row.half or None)
        (exempt if _different_cl_halves(candidate, other) or not _overlaps(candidate, other)
         else conflicting).append(row)
    return {"conflicting": conflicting, "exempt": exempt}