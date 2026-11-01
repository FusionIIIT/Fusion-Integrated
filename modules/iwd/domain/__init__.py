"""Pure Python domain engine for Institute Works Department (IWD).

Strict architectural boundary: Zero imports of Django, DRF, Celery, or database persistence.
"""

from modules.iwd.domain.cost_bands import (
    CostBand,
    LOW_COST_LIMIT,
    MID_COST_LIMIT,
    classify_cost_band,
)
from modules.iwd.domain.state_machine import (
    DomainValidationError,
    InvalidStateTransitionError,
    IWDDomainError,
    IWDState,
    ReworkLimitExceededError,
    route_initial_estimate,
    transition_billing_and_settlement,
    transition_complaint,
    transition_estimate_approval,
    transition_execution_and_verification,
    transition_inventory_and_procurement,
    transition_resubmission,
    transition_urgent_flag,
)
from modules.iwd.domain.workload import (
    EngineerCandidate,
    NoEligibleEngineerError,
    select_engineer_for_assignment,
)

__all__ = [
    "CostBand",
    "DomainValidationError",
    "EngineerCandidate",
    "IWDDomainError",
    "IWDState",
    "InvalidStateTransitionError",
    "LOW_COST_LIMIT",
    "MID_COST_LIMIT",
    "NoEligibleEngineerError",
    "ReworkLimitExceededError",
    "classify_cost_band",
    "route_initial_estimate",
    "select_engineer_for_assignment",
    "transition_billing_and_settlement",
    "transition_complaint",
    "transition_estimate_approval",
    "transition_execution_and_verification",
    "transition_inventory_and_procurement",
    "transition_resubmission",
    "transition_urgent_flag",
]
