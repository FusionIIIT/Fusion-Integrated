"""Leave Management data contracts.

THE ONLY thing other modules may import. All inter-module communication
through this file.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class LeaveCategoryResponse:
    """Leave category information."""
    code: str
    label: str
    description: str | None = None


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
    created_at: date | None = None


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
    approved_by: str | None = None
    approved_at: date | None = None
    cancelled_by: str | None = None
    cancelled_at: date | None = None
    resumed_by: str | None = None
    resumed_at: date | None = None
    created_at: date | None = None
    updated_at: date | None = None


@dataclass
class LeaveRequestAuditResponse:
    """Leave request audit log entry."""
    id: int
    request_id: int
    action: str
    previous_status: str | None
    new_status: str
    actor: str
    actor_type: str
    timestamp: date
    notes: str | None = None


@dataclass
class LeaveSanctionResponse:
    """Sanctioning authority decision."""
    id: int
    request_id: int
    authority: str
    authority_type: str
    decision: str
    decision_at: date
    notes: str | None = None


@dataclass
class LeavePolicyResponse:
    """Leave policy configuration."""
    policy_name: str
    version: str
    effective_from: date
    effective_to: date | None = None
    cl_entitlement: float
    rh_entitlement: float
    scl_entitlement: float
    el_carry_forward: bool
    is_active: bool
    created_at: date | None = None
    updated_at: date | None = None


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
    reason: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    duration_days: int | None = None


@dataclass
class LeaveBalanceQueryInput:
    """Input for querying leave balances."""
    user_id: int
    kind: str | None = None
    year: int | None = None


@dataclass
class LeaveRequestQueryInput:
    """Input for querying leave requests."""
    user_id: int | None = None
    category_code: str | None = None
    status: str | None = None
    request_type: str | None = None


@dataclass
class LeaveSanctionInput:
    """Input for adding a sanction."""
    request_id: int
    authority: str
    authority_type: str
    decision: str
    notes: str | None = None


@dataclass
class LeaveHolidayCalendarResponse:
    """Holiday calendar entry."""
    year: int
    holidays: list[dict]
    published_at: date | None = None
