"""PHC business rules that need no database."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

# The IAM's person kinds; an employee is anyone on the institute payroll.
EMPLOYEE_KINDS = frozenset({"faculty", "staff"})


class RuleViolation(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def require_employee(kind: str | None) -> None:
    # PHC-BR-04
    if kind not in EMPLOYEE_KINDS:
        raise RuleViolation(
            "not_an_employee",
            "Only institute employees can submit reimbursement claims; students are "
            "not eligible.")


@dataclass(frozen=True)
class SubmissionWindow:
    days: int
    includes_last_day: bool


def check_submission_window(expense_date: date, submitted_on: date,
                            window: SubmissionWindow) -> None:
    # PHC-BR-06
    age = (submitted_on - expense_date).days
    if age < 0:
        raise RuleViolation(
            "expense_in_future",
            "The medical expense date cannot be later than today. Check the date on "
            "the bill.")
    inside = age <= window.days if window.includes_last_day else age < window.days
    if not inside:
        raise RuleViolation(
            "outside_submission_window",
            f"Claims must be submitted within {window.days} days of the medical expense "
            "date, and this expense is older than that.")


def is_low_stock(level: Decimal, threshold: Decimal) -> bool:
    # PHC-BR-07: strictly below, so a level equal to the threshold raises nothing.
    return level < threshold


def apply_stock_change(level: Decimal, delta: Decimal) -> Decimal:
    if delta == 0:
        raise RuleViolation("zero_adjustment",
                            "Enter a quantity to add or deduct; zero changes nothing.")
    updated = level + delta
    if updated < 0:
        raise RuleViolation(
            "insufficient_stock",
            f"Only {level} in stock, so {abs(delta)} cannot be deducted.")
    return updated
