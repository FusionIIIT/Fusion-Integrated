"""Domain rules for the Institute Works Department (IWD) module.

Pure Python — no Django imports. This layer enforces business rules
independently of the ORM so they can be tested without a database.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Optional


class WorkCategory(str, Enum):
    CIVIL = "civil"
    ELECTRICAL = "electrical"
    PLUMBING = "plumbing"
    CARPENTRY = "carpentry"
    HOUSEKEEPING = "housekeeping"
    REPAIR = "repair"
    NEW_CONSTRUCTION = "new_construction"
    OTHER = "other"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class RequestStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CLOSED = "closed"


# Allowed status transitions — enforces the IWD workflow state machine
ALLOWED_TRANSITIONS: dict[RequestStatus, list[RequestStatus]] = {
    RequestStatus.DRAFT: [RequestStatus.SUBMITTED],
    RequestStatus.SUBMITTED: [RequestStatus.UNDER_REVIEW, RequestStatus.REJECTED],
    RequestStatus.UNDER_REVIEW: [RequestStatus.APPROVED, RequestStatus.REJECTED, RequestStatus.ON_HOLD],
    RequestStatus.APPROVED: [RequestStatus.IN_PROGRESS, RequestStatus.ON_HOLD],
    RequestStatus.IN_PROGRESS: [RequestStatus.COMPLETED, RequestStatus.ON_HOLD],
    RequestStatus.ON_HOLD: [RequestStatus.IN_PROGRESS, RequestStatus.REJECTED],
    RequestStatus.COMPLETED: [RequestStatus.CLOSED],
    RequestStatus.REJECTED: [],
    RequestStatus.CLOSED: [],
}


@dataclass
class WorkRequestDraft:
    title: str
    description: str
    location: str
    category: WorkCategory
    priority: Priority
    requester_username: str
    estimated_cost: float = 0.0
    required_by: Optional[date] = None


class IWDDomainError(Exception):
    pass


def validate_work_request(draft: WorkRequestDraft) -> list[str]:
    """Validate a work request before submission. Returns list of error strings."""
    errors: list[str] = []
    if not draft.title or len(draft.title.strip()) < 5:
        errors.append("Title must be at least 5 characters.")
    if not draft.description or len(draft.description.strip()) < 10:
        errors.append("Description must be at least 10 characters.")
    if not draft.location or len(draft.location.strip()) < 3:
        errors.append("Location must be specified.")
    if not draft.requester_username:
        errors.append("Requester username is required.")
    if draft.estimated_cost < 0:
        errors.append("Estimated cost cannot be negative.")
    if draft.required_by and draft.required_by < date.today():
        errors.append("Required-by date cannot be in the past.")
    return errors


def can_transition(current: RequestStatus, target: RequestStatus) -> bool:
    """Check if a status transition is allowed by the IWD workflow."""
    return target in ALLOWED_TRANSITIONS.get(current, [])


def validate_transition(current: RequestStatus, target: RequestStatus) -> None:
    """Raise IWDDomainError if the transition is not allowed."""
    if not can_transition(current, target):
        raise IWDDomainError(
            f"Cannot transition from '{current.value}' to '{target.value}'. "
            f"Allowed: {[s.value for s in ALLOWED_TRANSITIONS.get(current, [])]}"
        )


def compute_priority_score(priority: Priority, required_by: Optional[date]) -> int:
    """Compute a numeric priority score for work scheduling (higher = more urgent)."""
    base = {Priority.LOW: 1, Priority.MEDIUM: 2, Priority.HIGH: 3, Priority.URGENT: 4}[priority]
    if required_by is None:
        return base
    days_remaining = (required_by - date.today()).days
    if days_remaining <= 1:
        urgency_boost = 4
    elif days_remaining <= 7:
        urgency_boost = 2
    elif days_remaining <= 30:
        urgency_boost = 1
    else:
        urgency_boost = 0
    return base + urgency_boost


def requires_director_approval(estimated_cost: float) -> bool:
    """Work requests above Rs. 1,00,000 require Director-level approval."""
    return estimated_cost > 100_000


def requires_budget_allocation(category: WorkCategory, estimated_cost: float) -> bool:
    """New construction or high-cost repairs require formal budget allocation."""
    if category == WorkCategory.NEW_CONSTRUCTION:
        return True
    if estimated_cost > 500_000:
        return True
    return False

