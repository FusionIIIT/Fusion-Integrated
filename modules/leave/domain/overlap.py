"""Applicant non-overlap, with the half-day CL exception (BR-EL-012).

A new request must not impermissibly overlap the employee's active pending or
approved leave. The one carve-out is two CL half-days on the same date in
opposite halves: those occupy different halves of the day and so do not
overlap.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from modules.leave.domain.entitlement import CL


@dataclass(frozen=True)
class Interval:
    """The dates a single leave request occupies.

    ``half`` is set only for a half-day request (BR-EL-010), in which case
    ``start`` and ``end`` are the same day.
    """

    start: date
    end: date
    category: str
    half: str | None = None
    is_active: bool = True


def _spans_touch(a: Interval, b: Interval) -> bool:
    return a.start <= b.end and b.start <= a.end


def _opposite_half_day_cl(a: Interval, b: Interval) -> bool:
    """BR-EL-012 - first- and second-half CL on one date do not overlap."""
    if a.category != CL or b.category != CL:
        return False
    if a.half is None or b.half is None:
        return False
    if a.half == b.half:
        return False
    return a.start == a.end and b.start == b.end and a.start == b.start


def overlaps(a: Interval, b: Interval) -> bool:
    """Whether two active intervals impermissibly overlap."""
    if not (a.is_active and b.is_active):
        return False
    if not _spans_touch(a, b):
        return False
    return not _opposite_half_day_cl(a, b)


def conflicts_with(
    request: Interval,
    existing: tuple[Interval, ...],
) -> tuple[Interval, ...]:
    """BR-EL-012 - the active leave intervals a new request collides with."""
    return tuple(item for item in existing if overlaps(request, item))
