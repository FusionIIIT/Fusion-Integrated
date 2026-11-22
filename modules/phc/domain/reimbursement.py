"""PHC domain: reimbursement validation rules.

Pure Python - no Django or DRF imports (importlinter contract).
"""

from __future__ import annotations

import datetime


class ReimbursementValidationError(Exception):
    pass


def check_employee_eligibility(kind: str) -> None:
    """PHC-BR-04: Only employees may submit reimbursement claims."""
    if kind not in ("faculty", "staff"):
        raise ReimbursementValidationError(
            "Only institute employees are eligible to submit medical bill "
            "reimbursement claims. Students are excluded."
        )


def check_submission_window(
    expense_date: datetime.date,
    submission_date: datetime.date,
    window_days: int,
) -> None:
    """PHC-BR-06: Submission must fall within the configured window."""
    delta = (submission_date - expense_date).days
    if delta < 0:
        raise ReimbursementValidationError(
            "Expense date cannot be in the future relative to today."
        )
    if window_days > 0 and delta > window_days:
        raise ReimbursementValidationError(
            f"Claim submitted {delta} day(s) after the expense date, but the "
            f"allowed submission window is {window_days} day(s)."
        )
