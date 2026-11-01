"""Pure Python domain entities and value objects for Complaint Management System.

No Django or framework imports allowed here (enforced by import-linter).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class ComplaintStatus(StrEnum):
    SUBMITTED = "submitted"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"
    CLOSED = "closed"


class ComplaintPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EscalationType(StrEnum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"


class CMSRole(StrEnum):
    COMPLAINT_HANDLER = "complaint_handler"
    COMPLAINT_SUPERVISOR = "complaint_supervisor"


class ReopeningStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


TERMINAL_STATUSES = frozenset({ComplaintStatus.CLOSED, ComplaintStatus.REJECTED})
ACTIVE_STATUSES = frozenset({ComplaintStatus.SUBMITTED, ComplaintStatus.IN_PROGRESS})


@dataclass(frozen=True)
class ComplaintDTO:
    id: int | None
    complaint_id: str
    complainant_user_id: int
    category: str
    description: str
    priority: ComplaintPriority
    status: ComplaintStatus
    assigned_handler_id: int | None = None
    is_escalated: bool = False
    escalation_type: EscalationType | None = None
    resolution_details: str = ""
    rejection_reason: str = ""
    created_at: datetime | None = None
    resolved_at: datetime | None = None
    rejected_at: datetime | None = None
    closed_at: datetime | None = None


@dataclass(frozen=True)
class AttachmentDTO:
    file_name: str
    file_size: int
    content_type: str
    file_path: str


@dataclass(frozen=True)
class ProgressUpdateDTO:
    complaint_id: int
    user_id: int
    notes: str
    created_at: datetime | None = None


@dataclass(frozen=True)
class ClosureVerificationDTO:
    complaint_id: int
    verified_by_user_id: int
    verifier_role: str
    is_satisfied: bool
    comments: str = ""
    verified_at: datetime | None = None


@dataclass(frozen=True)
class FeedbackDTO:
    complaint_id: int
    complainant_user_id: int
    rating: int
    comments: str = ""


@dataclass(frozen=True)
class RoleAssignmentDTO:
    user_id: int
    role_name: CMSRole
    assigned_by_user_id: int
    valid_from: datetime
    valid_to: datetime | None
    is_active: bool = True

