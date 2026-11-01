"""Workflow routing and decision rules (BR-HR-009, BR-HR-023, BR-HR-029)."""
from __future__ import annotations

from enum import Enum

from modules.hreis.domain.exceptions import DomainValidationError


class DecisionOutcome(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    FORWARDED = "forwarded"



DEFAULT_APPROVAL_HIERARCHY: dict[str, list[str]] = {
    "faculty": ["hod", "director"],
    "staff": ["registrar"],
}


def get_next_authority(
    current_role: str,
    category: str,
    hierarchy_override: dict[str, list[str]] | None = None,
) -> str | None:
    """Determine the next authority in the configured hierarchy (BR-HR-009)."""
    hierarchy = hierarchy_override or DEFAULT_APPROVAL_HIERARCHY
    steps = hierarchy.get(category, ["hod", "director"])

    if current_role not in steps:
        return steps[0] if steps else None

    idx = steps.index(current_role)
    if idx + 1 < len(steps):
        return steps[idx + 1]
    return None  # Reached final authority


def validate_decision(
    *,
    outcome: str,
    current_status: str,
    remarks: str,
    can_forward: bool,
) -> None:
    """Enforce valid transitions and integrity of workflow order (BR-HR-023)."""
    valid_outcomes = {d.value for d in DecisionOutcome}
    if outcome not in valid_outcomes:
        raise DomainValidationError(
            f"Invalid decision outcome '{outcome}'. Must be one of: {', '.join(sorted(valid_outcomes))}."
        )

    if current_status in ("approved", "rejected", "settled", "finalized"):
        raise DomainValidationError(
            f"Cannot decide on request that is already in terminal state '{current_status}'."
        )

    if outcome == DecisionOutcome.FORWARDED.value and not can_forward:
        raise DomainValidationError(
            "Cannot forward request; current authority is the final authority in the hierarchy."
        )

    if outcome == DecisionOutcome.REJECTED.value and not remarks.strip():
        raise DomainValidationError("Remarks are required when rejecting a request.")
