"""Impermissible-overlap detection (BR-EL-012).

A new request must not overlap the employee's active pending or approved leave.
The one exception: two CL requests on the same date occupying different halves
do not overlap.
"""
from __future__ import annotations

from datetime import date


def overlaps(*, a_start: date, a_end: date, a_half: str,
             b_start: date, b_end: date, b_half: str) -> bool:
    """Whether two intervals overlap, honouring the half-day CL exception."""
    if a_end < b_start or b_end < a_start:
        return False
    same_single_day = (a_start == a_end == b_start == b_end)
    return not (same_single_day and a_half and b_half and a_half != b_half)


def first_conflict(*, candidate, existing) -> object | None:
    """The first existing record that conflicts with the candidate.

    Both arguments are dicts with start/end/half. Returns None when clear.
    """
    for row in existing:
        if overlaps(a_start=candidate["start"], a_end=candidate["end"],
                    a_half=candidate.get("half", ""),
                    b_start=row["start"], b_end=row["end"],
                    b_half=row.get("half", "")):
            return row
    return None
