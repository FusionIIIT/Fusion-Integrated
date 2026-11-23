"""Which alert is due and whether a deadline is missed (BR-PMS-097..104)."""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date

REVIEW = "review"
REVISION = "revision"
OFFICE_ACTION = "office_action"
MAINTENANCE = "maintenance"
KINDS = (REVIEW, REVISION, OFFICE_ACTION, MAINTENANCE)


def alert_due(due_on: date, today: date, offsets: Iterable[int]) -> int | None:
    """The tightest interval already reached, so a late-found deadline alerts once, not thrice."""
    remaining = (due_on - today).days
    if remaining < 0:
        return None
    reached = [k for k in offsets if remaining <= k]
    return min(reached) if reached else None


def missed(due_on: date, today: date) -> bool:
    return today > due_on
