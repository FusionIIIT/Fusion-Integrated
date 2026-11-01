"""Engineer auto-assignment algorithm based on workload and expertise.

Implements:
- BR-IWD-002: Automatic engineer assignment
- CFR-IWD-02: Assignment progression
- AFR-IWD-007: Workload distribution and relevant expertise
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


class IWDDomainError(Exception):
    """Base domain exception for IWD."""


class NoEligibleEngineerError(IWDDomainError):
    """Raised when no eligible engineer is available for assignment (BR-IWD-002)."""


@dataclass(frozen=True)
class EngineerCandidate:
    """Read-only candidate representation for assignment evaluation."""

    user_id: int
    active_complaint_count: int
    is_eligible: bool = True
    specialization: str = ""  # e.g., "civil", "electrical"


def select_engineer_for_assignment(
    candidates: Sequence[EngineerCandidate],
    required_specialization: str | None = None,
) -> EngineerCandidate:
    """Select the most appropriate Engineer for assignment using workload and expertise.

    Criteria:
    1. Candidate must be marked eligible (`is_eligible == True`).
    2. If `required_specialization` is specified, candidate must match specialization.
    3. Sort by lowest `active_complaint_count` (workload distribution).
    4. Deterministic tie-breaker: lowest `user_id`.

    Args:
        candidates: Sequence of candidate engineers with their current workloads.
        required_specialization: Optional required trade (e.g., "civil", "electrical").

    Returns:
        The selected EngineerCandidate.

    Raises:
        NoEligibleEngineerError: If no candidate satisfies eligibility/specialization criteria.
    """
    eligible = [
        c
        for c in candidates
        if c.is_eligible
        and (
            required_specialization is None
            or not c.specialization
            or c.specialization.lower() == required_specialization.lower()
        )
    ]

    if not eligible:
        raise NoEligibleEngineerError(
            f"No eligible engineer available for assignment"
            f"{f' with specialization {required_specialization!r}' if required_specialization else ''}."
        )

    # Sort deterministically: lowest active workload first, then lowest user_id
    eligible.sort(key=lambda c: (c.active_complaint_count, c.user_id))
    return eligible[0]

