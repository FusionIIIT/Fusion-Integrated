"""Resumption of duty after EL/COL/VL: CW-EL-04 and BR-EL-027/028."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from modules.leave.domain import categories as cat

DRAFT = "draft"
REVIEW_PENDING = "review_pending"
REVIEWED_NORMAL = "reviewed_normal"
REVIEWED_EARLY = "reviewed_early"
REVIEWED_LATE = "reviewed_late"

NORMAL, EARLY, LATE = "normal", "early", "late"

#: CW-EL-04 rows 1-4, as data; the outcome is computed, never chosen.
TRANSITIONS = {
    (DRAFT, "submit"): REVIEW_PENDING,
    (REVIEW_PENDING, NORMAL): REVIEWED_NORMAL,
    (REVIEW_PENDING, EARLY): REVIEWED_EARLY,
    (REVIEW_PENDING, LATE): REVIEWED_LATE,
}


class ResumptionRefused(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Outcome:
    kind: str
    actual_end: date
    #: Positive restores days to the balance; negative charges more.
    adjustment: Decimal


def move(frm: str, event: str) -> str:
    try:
        return TRANSITIONS[(frm, event)]
    except KeyError:
        raise ResumptionRefused("invalid_transition",
                                f"A resumption in {frm!r} cannot take {event!r}.") from None


def check_submission(*, category: str, leave_start: date, resumption_date: date,
                     today: date) -> None:
    if not cat.get(category).extendable:
        raise ResumptionRefused("resumption_not_applicable",
                                "Formal resumption applies only to EL, COL and VL.")
    if resumption_date > today:
        raise ResumptionRefused("resumption_in_future",
                                "Submit your resumption on or after the day you return.")
    if resumption_date <= leave_start:
        raise ResumptionRefused("resumption_before_leave",
                                "The resumption date must be after the leave began. If you "
                                "never went on leave, it should have been cancelled.")


def classify(*, approved_end: date, resumption_date: date) -> Outcome:
    """Back on the day after the last approved day is normal; earlier is early; later is late."""
    actual_end = resumption_date - timedelta(days=1)
    if actual_end == approved_end:
        return Outcome(NORMAL, approved_end, Decimal(0))
    return Outcome(EARLY if actual_end < approved_end else LATE, actual_end,
                   Decimal((approved_end - actual_end).days))
