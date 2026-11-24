"""Pure Python official department detail change lifecycle (BW-DEPT-05, BW-DEPT-06, CW-DEPT-03)."""

from __future__ import annotations

from modules.dept.domain.exceptions import InvalidTransitionError, ValidationError

OFFICIAL_FIELDS = {"name", "core_policies", "description"}

OFFICIAL_CHANGE_TRANSITIONS: dict[tuple[str, str, str], str] = {
    ("PENDING", "APPROVE", "HOD"): "APPROVED",
    ("PENDING", "REJECT", "HOD"): "REJECTED",
}


def validate_official_change_proposal(field_name: str, new_value: str, justification: str) -> None:
    """Validate official department detail proposal (BR-DEPT-011)."""
    if field_name not in OFFICIAL_FIELDS:
        raise ValidationError(
            f"Field '{field_name}' is not an authorized official department field."
        )
    if not new_value or not new_value.strip():
        raise ValidationError("Proposed new value cannot be empty.")
    if not justification or not justification.strip():
        raise ValidationError("Justification is required for official department changes.")


def transition_official_change(current_state: str, event: str, acting_role: str) -> str:
    """Transition official detail change request."""
    key = (current_state, event, acting_role)
    next_state = OFFICIAL_CHANGE_TRANSITIONS.get(key)
    if not next_state:
        raise InvalidTransitionError(
            f"Cannot transition official change from {current_state} via {event} by {acting_role}."
        )
    return next_state
