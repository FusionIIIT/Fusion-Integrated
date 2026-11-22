"""Pure Python stock request domain logic and state transitions (BW-DEPT-01, BW-DEPT-02)."""

from __future__ import annotations

from modules.dept.domain.exceptions import (
    AvailabilityError,
    InvalidTransitionError,
    ValidationError,
)

# Declarative transition table: (current_state, event, acting_role) -> next_state
STOCK_TRANSITIONS: dict[tuple[str, str, str], str] = {
    ("SUBMITTED", "APPROVE", "HOD"): "APPROVED",
    ("SUBMITTED", "REJECT", "HOD"): "REJECTED",
    ("APPROVED", "ISSUE", "DEPT_ADMIN"): "ISSUED",
}


def validate_stock_request_creation(requested_quantity: int, available_quantity: int) -> None:
    """Validate initial stock request submission (BR-DEPT-005, BR-DEPT-015)."""
    if requested_quantity <= 0:
        raise ValidationError("Requested quantity must be greater than zero.")
    if requested_quantity > available_quantity:
        raise AvailabilityError(
            f"Requested quantity ({requested_quantity}) exceeds "
            f"available inventory ({available_quantity})."
        )


def transition_stock_request(
    current_state: str,
    event: str,
    acting_role: str,
    requested_quantity: int,
    available_quantity: int,
) -> str:
    """Transition stock request through its lifecycle states."""
    key = (current_state, event, acting_role)
    next_state = STOCK_TRANSITIONS.get(key)
    if not next_state:
        raise InvalidTransitionError(
            f"Cannot transition stock request from {current_state} via {event} by {acting_role}."
        )

    if event == "ISSUE" and requested_quantity > available_quantity:
        raise AvailabilityError(
            f"Cannot issue stock: requested quantity ({requested_quantity}) "
            f"exceeds available ({available_quantity})."
        )

    return next_state
