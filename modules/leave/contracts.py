"""Leave Management data contracts.

THE ONLY thing other modules may import. All inter-module communication
through this file.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class LeaveCategoryResponse:
    """Leave category information."""
    code: str
    label: str
    description: Optional[str] = None


@dataclass
class LeaveBalanceResponse:
    """Employee leave balance."""
    user_id: int
    kind: str
    category_code: str
    year: int
    available: float
    used: float
    carried_over: float
    entitlement: float
    created_at: Optional[date] = None


@dataclass
class LeaveRequestResponse:
    """Leave request application."""
    id: int
    user_id: int
    category_code: str
    category_label: str
    status: str
    request_type: str
    start_date: date
    end_date: date
    duration_days: int
    reason: str
    station_leave: bool
    approved_by: Optional[str] = None
    approved_at: Optional[date] = None
    cancelled_by: Optional[str] = None
    cancelled_at: Optional[date] = None
    resumed_by: Optional[str] = None
    resumed_at: Optional[date] = None
    created_at: Optional[date] = None
    updated_at: Optional[date] = None


@dataclass
class LeaveRequestAuditResponse:
    """Leave request audit log entry."""
    id: int
    request_id: int
    action: str
    previous_status: Optional[str]
    new_status: str
    actor: str
    actor_type: str
    timestamp: date
    notes: Optional[str] = None


@dataclass
class LeaveSanctionResponse:
    """Sanctioning authority decision."""
    id: int
    request_id: int
    authority: str
    authority_type: str
    decision: str
    decision_at: date
    notes: Optional[str] = None


@dataclass
class LeavePolicyResponse:
    """Leave policy configuration."""
    policy_name: str
    version: str
    effective_from: date
    effective_to: Optional[date] = None
    cl_entitlement: float
    rh_entitlement: float
    scl_entitlement: float
    el_carry_forward: bool
    is_active: bool
    created_at: Optional[date] = None
    updated_at: Optional[date] = None


@dataclass
class LeaveRequestCreateInput:
    """Input for creating a leave request."""
    user_id: int
    category_code: str
    start_date: date
    end_date: date
    reason: str
    station_leave: bool = False


@dataclass
class LeaveRequestUpdateInput:
    """Input for updating a leave request (draft only)."""
    reason: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    duration_days: Optional[int] = None


@dataclass
class LeaveBalanceQueryInput:
    """Input for querying leave balances."""
    user_id: int
    kind: Optional[str] = None
    year: Optional[int] = None


@dataclass
class LeaveRequestQueryInput:
    """Input for querying leave requests."""
    user_id: Optional[int] = None
    category_code: Optional[str] = None
    status: Optional[str] = None
    request_type: Optional[str] = None


@dataclass
class LeaveSanctionInput:
    """Input for adding a sanction."""
    request_id: int
    authority: str
    authority_type: str
    decision: str
    notes: Optional[str] = None


@dataclass
class LeaveHolidayCalendarResponse:
    """Holiday calendar entry."""
    year: int
    holidays: list[dict]
    published_at: Optional[date] = None
