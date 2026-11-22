"""Pure Python department role tenure and transition validations (BR-DEPT-021..024, CW-DEPT-04)."""

from __future__ import annotations

import datetime

from modules.dept.domain.exceptions import InvalidTransitionError, ValidationError

VALID_ROLES = {"HOD", "DEPT_ADMIN"}


def validate_role_tenure(
    role_name: str,
    start_date: datetime.datetime,
    end_date: datetime.datetime,
) -> None:
    """Validate role assignment time interval (BR-DEPT-023)."""
    if role_name not in VALID_ROLES:
        raise ValidationError(f"Role '{role_name}' is not a valid department governance role.")
    if start_date >= end_date:
        raise ValidationError("Role assignment start_date must be strictly before end_date.")


def transition_role_assignment(current_state: str, event: str, acting_role: str) -> str:
    """Transition role assignment status."""
    transitions = {
        ("SCHEDULED", "ACTIVATE", "SYSTEM"): "ACTIVE",
        ("SCHEDULED", "REVOKE", "INSTITUTE_ADMIN"): "REVOKED",
        ("ACTIVE", "REVOKE", "INSTITUTE_ADMIN"): "REVOKED",
        ("ACTIVE", "EXPIRE", "SYSTEM"): "EXPIRED",
    }
    next_state = transitions.get((current_state, event, acting_role))
    if not next_state:
        raise InvalidTransitionError(
            f"Cannot transition role assignment from {current_state} via {event} by {acting_role}."
        )
    return next_state
