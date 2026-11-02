"""Pure domain entities and types for ELM."""
from __future__ import annotations

from dataclasses import dataclass
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
    AWAITING_SANCTION = "awaiting_sanction"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    CANCELLED = "cancelled"
    RESUMED = "resumed"


@dataclass(frozen=True)
class StateTransitionResult:
    is_valid: bool
    next_status: LeaveStatus
    message: str = ""
