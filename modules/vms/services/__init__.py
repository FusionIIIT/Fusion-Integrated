"""VMS Services Package."""

from modules.vms.services.errors import (
    BlacklistMatchError,
    DuplicatePassError,
    InvalidTransitionError,
    PassExpiredError,
    UnauthorizedZoneError,
    VisitNotFoundError,
)
from modules.vms.services.gate import (
    execute_check_out,
    reconcile_offline_gate_events,
    transition_visit_state,
    verify_qr_and_check_in,
    verify_zone_access,
)
from modules.vms.services.registration import (
    approve_visit,
    get_or_create_visitor,
    reject_visit,
    request_or_create_visit,
)
from modules.vms.services.security import (
    add_to_blacklist,
    resolve_emergency_muster,
    resolve_gate_alert,
    trigger_emergency_muster,
)

__all__ = [
    "BlacklistMatchError",
    "DuplicatePassError",
    "InvalidTransitionError",
    "PassExpiredError",
    "UnauthorizedZoneError",
    "VisitNotFoundError",
    "add_to_blacklist",
    "approve_visit",
    "execute_check_out",
    "get_or_create_visitor",
    "reconcile_offline_gate_events",
    "reject_visit",
    "request_or_create_visit",
    "resolve_emergency_muster",
    "resolve_gate_alert",
    "transition_visit_state",
    "trigger_emergency_muster",
    "verify_qr_and_check_in",
    "verify_zone_access",
]
