"""The stable ELM public surface for other domain modules."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Sequence


@dataclass(frozen=True)
class EmploymentProjection:
    """HR-owned employee facts used by ELM eligibility and routing."""
    user_id: int
    kind: str
    designation: str
    unit_code: str
    unit_head_user_id: int | None
    is_director: bool = False
    active: bool = True


@dataclass(frozen=True)
class VacationPeriodProjection:
    """Academic Calendar vacation interval supplied to ELM."""
    external_id: str
    label: str
    start_date: date
    end_date: date
    academic_year: str


@dataclass(frozen=True)
class ProjectionSyncResult:
    employees_written: int = 0
    vacation_periods_written: int = 0


@dataclass(frozen=True)
class LeaveBalanceDTO:
    employee_id: int
    category_code: str
    year: int
    entitlement: Decimal
    carried_over: Decimal
    available: Decimal


@dataclass(frozen=True)
class LeaveAccountEntryDTO:
    employee_id: int
    category_code: str
    year: int
    amount: Decimal
    kind: str
    source_key: str
    created_at: datetime


@dataclass(frozen=True)
class EmploymentQuery:
    user_ids: Sequence[int]
