"""Pure Python feedback lifecycle state machine (BW-DEPT-03, BW-DEPT-04, CW-DEPT-02)."""

from __future__ import annotations

from modules.dept.domain.exceptions import InvalidTransitionError, ValidationError

FEEDBACK_TRANSITIONS: dict[tuple[str, str, str], str] = {
    ("NEW", "START_REVIEW", "DEPT_ADMIN"): "UNDER_REVIEW",
    ("NEW", "RESOLVE", "DEPT_ADMIN"): "RESOLVED",
    ("NEW", "CLOSE", "DEPT_ADMIN"): "CLOSED",
    ("UNDER_REVIEW", "RESOLVE", "DEPT_ADMIN"): "RESOLVED",
    ("UNDER_REVIEW", "RESOLVE", "HOD"): "RESOLVED",
    ("UNDER_REVIEW", "CLOSE", "DEPT_ADMIN"): "CLOSED",
    ("UNDER_REVIEW", "CLOSE", "HOD"): "CLOSED",
}


VALID_CATEGORIES = {"ACADEMIC", "INFRASTRUCTURE", "ADMINISTRATIVE", "OTHER"}


def validate_feedback_submission(title: str, description: str, category: str) -> None:
    """Validate feedback submission completeness (BR-DEPT-008)."""
    if not title or not title.strip():
        raise ValidationError("Feedback title is required.")
    if not description or not description.strip():
        raise ValidationError("Feedback description is required.")
    if not category or category.upper().strip() not in VALID_CATEGORIES:
        raise ValidationError(f"Invalid feedback category '{category}'.")


def transition_feedback(current_state: str, event: str, acting_role: str) -> str:
    """Transition feedback through review and resolution states."""
    key = (current_state, event, acting_role)
    next_state = FEEDBACK_TRANSITIONS.get(key)
    if not next_state:
        raise InvalidTransitionError(
            f"Cannot transition feedback from {current_state} via {event} by {acting_role}."
        )
    return next_state
