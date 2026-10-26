"""Utility for checking overlap between leave requests.

The function implements the logic described in BR-EL-012.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

HalfPeriod = Literal["first_half", "second_half"]
LeaveType = str


def requests_overlap(
    new_start: date,
    new_end: date,
    old_start: date,
    old_end: date,
    new_type: LeaveType,
    old_type: LeaveType,
    new_period: str,
    old_period: str,
) -> bool:
    """Return ``True`` if two leave requests overlap.

    Parameters
    ----------
    new_start, new_end, old_start, old_end:
        Inclusive date ranges of the two requests.
    new_type, old_type:
        Leave type identifiers.
    new_period, old_period:
        Period identifiers (e.g. ``"first_half"`` or ``"second_half"``).

    The rules are:
    * If the date ranges are disjoint, return ``False``.
    * If the ranges overlap on a single date and **both** requests are of type
      ``"CL"`` **and** both periods are half‑periods with different values,
      return ``False``.
    * In all other overlapping cases, return ``True``.
    """

    # Disjoint ranges
    if new_end < old_start or old_end < new_start:
        return False

    # Overlap exists. Check for the special single‑date half‑period case.
    if new_start == new_end == old_start == old_end:
        if (
            new_type == "CL"
            and old_type == "CL"
            and new_period in {"first_half", "second_half"}
            and old_period in {"first_half", "second_half"}
            and new_period != old_period
        ):
            return False
        return True

    # General overlapping case
    return True
