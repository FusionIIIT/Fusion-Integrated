"""Pure policy constants and predicates for PHC (PHC-BR-04..07)."""
from __future__ import annotations

import datetime as dt
from typing import Any

CLAIM_WINDOW_DAYS = 90
#: PostgreSQL int4 ceiling, shared by input validation and by cumulative stock
#: maths so a sequence of otherwise-valid adds cannot overflow the column.
MAX_INT4 = 2_147_483_647
REIMBURSABLE_KINDS = frozenset({"employee", "staff", "faculty"})
OUTBOX_TOPICS = frozenset({
    "claim.submitted", "claim.status_changed", "requisition.decided",
    "inventory.low_stock",
})

NOT_FOUND_MESSAGE = "No matching record was found for your account."
WAITING_MESSAGE = "The record is still at an earlier stage; try again when it reaches this stage."
ALREADY_DONE_MESSAGE = "This action was already completed; refresh the page before trying again."
CLAIM_KIND_MESSAGE = ("Only employees may submit reimbursement claims. "
                      "Ask your PHC office to correct your profile.")
CLAIM_WINDOW_MESSAGE = f"Claims must be filed within {CLAIM_WINDOW_DAYS} days of the expense date."
PRESCRIPTION_MESSAGE = ("Link this claim to one of your own recorded prescriptions "
                        "before submitting.")
STOCK_MESSAGE = "The deduction exceeds stock on hand; reduce the quantity and try again."
STOCK_OVERFLOW_MESSAGE = ("This addition would exceed the maximum stock level; "
                          "reduce the quantity and try again.")
UNKNOWN_ITEM_MESSAGE = ("An item in your requisition does not exist; check the item "
                        "list and resubmit.")
SCHEDULE_DUPLICATE_MESSAGE = ("This doctor already has a schedule for that day; "
                              "edit the existing entry instead.")


class PolicyViolation(ValueError):
    """A pure rule was broken. Services translate this into an API error."""


class StockOverflow(PolicyViolation):
    """The new stock level would not fit in an int4 column."""


def is_reimbursable_kind(kind: Any) -> bool:
    return isinstance(kind, str) and kind.strip().lower() in REIMBURSABLE_KINDS


def expense_within_window(expense_date: dt.date, today: dt.date,
                          window_days: int = CLAIM_WINDOW_DAYS) -> bool:
    """True when the expense is not in the future and is inside the past window."""
    if not isinstance(expense_date, dt.date) or not isinstance(today, dt.date):
        raise PolicyViolation("expense_within_window needs two dates.")
    if window_days < 0:
        raise PolicyViolation("window_days cannot be negative.")
    age = (today - expense_date).days
    return 0 <= age <= window_days


def stock_after_adjustment(current: int, quantity: int,
                           direction: str) -> int | None:
    """Return the new level, or None when a deduction exceeds stock on hand."""
    if quantity <= 0:
        raise PolicyViolation("quantity must be positive.")
    if direction == "add":
        new_level = current + quantity
        if new_level > MAX_INT4:
            raise StockOverflow(STOCK_OVERFLOW_MESSAGE)
        return new_level
    if direction == "deduct":
        return None if quantity > current else current - quantity
    raise PolicyViolation(f"Unknown direction {direction!r}.")


def is_low_stock(quantity: int, threshold: int) -> bool:
    """PHC-BR-07: strictly below the threshold, never equal to it."""
    return quantity < threshold
