"""Domain entities and value objects for Leave Management (ELM).

Implements analysis models from Lab 5 / CS3010:
- HR-E-01: LeaveRequest
- HR-E-02: Employee (represented by user_id and profile data)
- HR-E-03: LeaveBalance
- HR-E-04: ApprovalDecision
- HR-E-05: ApprovingAuthority
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class LeaveType(str, Enum):
    """Supported leave types per BR-HR-034."""
    CASUAL = "casual"
    RESTRICTED = "restricted"
    MEDICAL = "medical"
    EARNED = "earned"
    VACATION = "vacation"
    SABBATICAL = "sabbatical"


class LeaveStatus(str, Enum):
    """Lifecycle states for LeaveRequest governed by BW-HR-01, BW-HR-02, BW-HR-03 STT."""
    DRAFT = "draft"
    PENDING_CURRENT_AUTHORITY = "pending_current_authority"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ApprovalOutcome(str, Enum):
    """Decision outcomes supported per BR-HR-023."""
    APPROVED = "approved"
    REJECTED = "rejected"
    FORWARDED = "forwarded"


class AuthorityRole(str, Enum):
    """Authority tiers defined per BR-HR-009 routing rules."""
    HOD = "HOD"
    REGISTRAR = "Registrar"
    DIRECTOR = "Director"


class EmployeeCategory(str, Enum):
    """Employee categories governing approval hierarchy routing."""
    FACULTY = "faculty"
    STAFF = "staff"
    STUDENT = "student"


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)


@dataclass
class LeaveBalanceEntity:
    user_id: int
    leave_type: LeaveType
    year: int
    total_entitlement: Decimal
    consumed_days: Decimal
    available_balance: Decimal

    def has_sufficient_balance(self, requested_days: Decimal) -> bool:
        return self.available_balance >= requested_days

    def deduct(self, days: Decimal) -> None:
        if days > self.available_balance:
            raise ValueError(
                f"Cannot deduct {days} days from available balance {self.available_balance}."
            )
        self.consumed_days += days
        self.available_balance -= days


@dataclass
class LeaveRequestEntity:
    id: int | None
    user_id: int
    leave_type: LeaveType
    start_date: date
    end_date: date
    duration_days: Decimal
    justification: str
    status: LeaveStatus = LeaveStatus.DRAFT
    current_authority_id: int | None = None
    current_authority_role: str = ""
    forward_count: int = 0
    cancellation_reason: str = ""
    created_at: datetime | None = None
