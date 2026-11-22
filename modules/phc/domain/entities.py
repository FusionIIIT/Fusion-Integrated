"""Pure Python domain entities and value objects.

Must never import Django, DRF or Celery (enforced by import-linter).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum


class DoctorAttendanceStatus(str, Enum):
    AVAILABLE = "Available"
    DEPARTED = "Departed"
    ON_LEAVE = "On-Leave"


class ReimbursementStatus(str, Enum):
    PENDING_PHC_REVIEW = "Pending PHC Review"
    PENDING_ACCOUNTS_VERIFICATION = "Pending Accounts Verification"
    PENDING_SANCTION = "Pending Sanction"
    APPROVED_FOR_PAYMENT = "Approved for Payment"
    REJECTED = "Rejected"
    REIMBURSED = "Reimbursed"


class RequisitionStatus(str, Enum):
    PENDING_APPROVAL = "Pending Approval"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    FULFILLED = "Fulfilled"


@dataclass(frozen=True)
class ReimbursementRuleEvaluation:
    is_employee: bool
    has_valid_prescription: bool
    within_window: bool
    expense_date: date
    submission_date: date
    window_days: int = 90

    @property
    def is_eligible(self) -> bool:
        return (
            self.is_employee
            and self.has_valid_prescription
            and self.within_window
        )


@dataclass(frozen=True)
class StockThresholdEvaluation:
    item_code: str
    current_stock: int
    reorder_threshold: int

    @property
    def is_low_stock(self) -> bool:
        # PHC-BR-07: stock_level < reorder_threshold
        return self.current_stock < self.reorder_threshold
