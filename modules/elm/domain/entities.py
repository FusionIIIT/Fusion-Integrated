
"""Domain types for Employee Leave Management."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from uuid import UUID


class LeaveStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    CANCELLED = "cancelled"
    EXTENSION_REQUESTED = "extension_requested"
    RESUMED = "resumed"


@dataclass(frozen=True)
class LeavePeriod:
    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        if self.end_date < self.start_date:
            raise ValueError("Leave end date cannot be before start date.")

    @property
    def calendar_days(self) -> int:
        return (self.end_date - self.start_date).days + 1


@dataclass(frozen=True)
class LeaveApplicationSummary:
    id: UUID
    employee_id: str
    leave_type: str
    period: LeavePeriod
    status: LeaveStatus
