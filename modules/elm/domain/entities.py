"""Pure domain entities and types for ELM."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class LeaveCategory(str, Enum):
    CL = "CL"        # Casual Leave
    RH = "RH"        # Restricted Holiday
    SCL = "SCL"      # Special Casual Leave
    EL = "EL"        # Earned Leave
    VL = "VL"        # Vacation Leave
    COL = "COL"      # Commuted Leave (Medical)


class LeaveStatus(str, Enum):
    DRAFT = "draft"
    AWAITING_SUBSTITUTE = "awaiting_substitute"
    SUBSTITUTE_DECLINED = "substitute_declined"
    AWAITING_UNIT_HEAD = "awaiting_unit_head"
    AWAITING_DIRECTOR_SELF_SANCTION = "awaiting_director_self_sanction"
    AWAITING_ESTABLISHMENT = "awaiting_establishment"
    AWAITING_FINAL_SANCTION = "awaiting_final_sanction"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    CANCELLATION_PENDING_UNIT_HEAD = "cancellation_pending_unit_head"
    CANCELLATION_PENDING_ESTABLISHMENT = "cancellation_pending_establishment"
    CANCELLATION_PENDING_FINAL = "cancellation_pending_final"
    CANCELLED = "cancelled"
    EXTENSION_PENDING_SUBSTITUTE = "extension_pending_substitute"
    EXTENSION_PENDING_UNIT_HEAD = "extension_pending_unit_head"
    EXTENSION_PENDING_FINAL = "extension_pending_final"
    EXTENDED = "extended"
    RESUMPTION_PENDING = "resumption_pending"
    RESUMED = "resumed"


@dataclass(frozen=True)
class LeaveValidationResult:
    is_valid: bool
    calculated_days: float
    error_message: str | None = None


@dataclass(frozen=True)
class StateTransitionResult:
    success: bool
    new_status: LeaveStatus
    message: str
    balance_deduction: float = 0.0
    balance_refund: float = 0.0
