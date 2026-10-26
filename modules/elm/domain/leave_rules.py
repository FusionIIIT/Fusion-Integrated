"""Pure leave rules (no Django).

Simplification: days are counted as calendar days, so weekends and
holidays are not excluded.
"""

from datetime import date
from decimal import Decimal


def count_leave_days(start: date, end: date, part_of_day: str) -> Decimal:
    """Return the number of leave days requested (0.5 for a half day)."""
    if end < start:
        raise ValueError("end date cannot be before start date")
    if part_of_day != "full":
        if start != end:
            raise ValueError("a half day must be a single date")
        return Decimal("0.5")
    return Decimal((end - start).days + 1)


def has_enough_balance(available: Decimal, requested: Decimal) -> bool:
    """Return True if the available days cover the requested days."""
    return available >= requested


def can_review(reviewer_id: int, applicant_id: int) -> bool:
    """Return False when a reviewer is trying to review their own request."""
    return reviewer_id != applicant_id
