"""VMS Pure Domain Layer.
Strictly pure Python: no Django, no DRF, no Celery, no database.
"""

from modules.vms.domain.models import (
    BlacklistMatchResult,
    PassAllowanceResult,
    PassScope,
    VisitDecision,
    VisitorIdentity,
    ZoneAccessResult,
)
from modules.vms.domain.rules import (
    calculate_walk_in_duration,
    check_overstay,
    validate_blacklist_match,
    validate_same_day_pass,
    validate_zone_access,
)
from modules.vms.domain.state_machine import (
    ALLOWED_TRANSITIONS,
    TERMINAL_STATES,
    InvalidStateTransitionError,
    TransitionTrigger,
    VisitState,
    validate_transition,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "TERMINAL_STATES",
    "BlacklistMatchResult",
    "InvalidStateTransitionError",
    "PassAllowanceResult",
    "PassScope",
    "TransitionTrigger",
    "VisitDecision",
    "VisitState",
    "VisitorIdentity",
    "ZoneAccessResult",
    "calculate_walk_in_duration",
    "check_overstay",
    "validate_blacklist_match",
    "validate_same_day_pass",
    "validate_transition",
    "validate_zone_access",
]
