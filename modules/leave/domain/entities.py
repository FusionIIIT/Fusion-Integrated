"""Pure domain entities for Leave Management — no Django imports."""
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Optional


class LeaveCategory(StrEnum):
    CL = "CL"   # Casual Leave
    RH = "RH"   # Restricted Holiday
    SCL = "SCL" # Special Casual Leave
    EL = "EL"   # Earned Leave
    VL = "VL"   # Vacation Leave
    COL = "COL" # Commuted Leave


class LeaveStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    SUBSTITUTE_PENDING = "substitute_pending"
    UNIT_HEAD_REVIEW = "unit_head_review"
    ESTABLISHMENT_REVIEW = "establishment_review"
    FINAL_SANCTION = "final_sanction"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    CANCELLED = "cancelled"
    EXTENSION_REQUESTED = "extension_requested"
    RESUMPTION_PENDING = "resumption_pending"
    RESUMED = "resumed"


class EmployeeType(StrEnum):
    FACULTY = "faculty"
    NON_FACULTY = "non_faculty"


@dataclass(frozen=True)
class LeaveEntitlement:
    category: LeaveCategory
    annual_entitlement: float
    carries_forward: bool
    half_day_allowed: bool
    requires_medical_certificate: bool
    max_per_request: Optional[float] = None


@dataclass(frozen=True)
class LeaveBalance:
    user_id: int
    category: LeaveCategory
    year: int
    opening_balance: float
    credited: float
    availed: float
    lapsed: float
    closing_balance: float


@dataclass(frozen=True)
class LeaveRequestDTO:
    id: Optional[int]
    user_id: int
    category: LeaveCategory
    start_date: date
    end_date: date
    half_day: bool
    half_day_session: Optional[str]  # "forenoon" or "afternoon"
    purpose: str
    station_leave: bool
    station_leave_address: Optional[str]
    substitute_id: Optional[int]
    status: LeaveStatus
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass(frozen=True)
class SubstituteRequestDTO:
    id: Optional[int]
    leave_request_id: int
    substitute_id: int
    status: str  # pending, accepted, declined
    created_at: Optional[str] = None
    responded_at: Optional[str] = None


@dataclass(frozen=True)
class LeavePolicyDTO:
    category: LeaveCategory
    employee_type: EmployeeType
    annual_entitlement: float
    carries_forward: bool
    half_day_allowed: bool
    requires_medical_certificate: bool
    effective_from: date
    effective_to: Optional[date]


@dataclass(frozen=True)
class HolidayDTO:
    date: date
    name: str
    is_restricted: bool
    year: int