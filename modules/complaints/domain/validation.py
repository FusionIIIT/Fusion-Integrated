"""Domain validation rules for Complaint Management System.

Zero framework imports.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Sequence

from .entities import ComplaintPriority, ComplaintStatus
from .errors import (
    AttachmentConstraintError,
    EscalationNotAllowed,
    FeedbackNotAllowed,
    MandatoryFieldMissing,
    ReopeningNotAllowed,
    RoleCardinalityError,
    RuleViolation,
)

MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_ATTACHMENT_EXTENSIONS = frozenset({
    ".pdf", ".jpg", ".jpeg", ".png", ".txt", ".doc", ".docx", ".zip"
})


def validate_submission_fields(category: str | None, description: str | None) -> None:
    """Validate mandatory complaint fields (BR-CMS-002)."""
    if not category or not str(category).strip():
        raise MandatoryFieldMissing("category")
    if not description or not str(description).strip():
        raise MandatoryFieldMissing("description")


def validate_priority(priority: str) -> ComplaintPriority:
    """Validate priority value set (BR-CMS-009)."""
    val = str(priority).strip().lower()
    try:
        return ComplaintPriority(val)
    except ValueError:
        raise RuleViolation(
            f"Invalid priority '{priority}'. Must be one of Low, Medium, High (BR-CMS-009).",
            code="invalid_priority",
        )


def validate_attachment(file_name: str, file_size: int) -> None:
    """Validate attachment constraints (BR-CMS-004, BR-CMS-005)."""
    if file_size > MAX_ATTACHMENT_SIZE_BYTES:
        raise AttachmentConstraintError(
            f"Attachment size ({file_size} bytes) exceeds maximum allowed {MAX_ATTACHMENT_SIZE_BYTES} bytes."
        )

    _, ext = os.path.splitext(file_name.lower())
    if ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
        raise AttachmentConstraintError(
            f"Attachment type '{ext}' is not permitted. Allowed: {', '.join(sorted(ALLOWED_ATTACHMENT_EXTENSIONS))}."
        )


def validate_reopening_eligibility(status: str) -> None:
    """Validate complaint is eligible for reopening (BR-CMS-018: Closed only)."""
    if status != ComplaintStatus.CLOSED:
        raise ReopeningNotAllowed(
            f"Only Closed complaints can be reopened (current: '{status}') (BR-CMS-018)."
        )


def validate_feedback_eligibility(status: str, rating: int) -> None:
    """Validate feedback eligibility and rating range (BR-CMS-022)."""
    if status not in (ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED):
        raise FeedbackNotAllowed(
            f"Feedback can only be submitted for Resolved or Closed complaints (current: '{status}') (BR-CMS-022)."
        )
    if rating < 1 or rating > 5:
        raise RuleViolation(
            f"Feedback rating must be between 1 and 5 (received: {rating}).",
            code="invalid_rating",
        )


def validate_escalation_eligibility(status: str, is_escalated: bool) -> None:
    """Validate manual or automatic escalation eligibility (BR-CMS-024)."""
    if status not in (ComplaintStatus.SUBMITTED, ComplaintStatus.IN_PROGRESS):
        raise EscalationNotAllowed(
            f"Only unresolved complaints (Submitted or In Progress) can be escalated (current: '{status}') (BR-CMS-024)."
        )
    if is_escalated:
        raise EscalationNotAllowed("Complaint is already escalated (BR-CMS-025).")


def validate_role_assignment(
    role_name: str,
    valid_from: datetime,
    valid_to: datetime | None,
) -> None:
    """Validate CMS role assignment dates and roles (BR-CMS-035, BR-CMS-038)."""
    if role_name not in ("complaint_handler", "complaint_supervisor"):
        raise RoleCardinalityError(
            role_name,
            f"Invalid CMS role '{role_name}'. Must be complaint_handler or complaint_supervisor (BR-CMS-038).",
        )
    if valid_to and valid_to <= valid_from:
        raise RuleViolation(
            "Role assignment 'valid_to' must be after 'valid_from'.",
            code="invalid_role_duration",
        )

