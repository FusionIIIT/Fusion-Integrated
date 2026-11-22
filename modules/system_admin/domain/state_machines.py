"""Declarative state machine transition tables for System Admin workflows."""
from __future__ import annotations

from modules.system_admin.domain.exceptions import InvalidStateTransitionError

# (current_state, event, actor) -> resulting_state
USER_LIFECYCLE_TRANSITIONS: dict[tuple[str, str, str], str] = {
    # Active user deactivation (UC-SA-004)
    ("active", "deactivate", "super_admin"): "deactivated",
    # Deactivated user reactivation (UC-SA-005 / BW-SA-06)
    ("deactivated", "reactivate", "super_admin"): "active",
    # Deactivated user archival (UC-SA-015 / BW-SA-07, BW-SA-08)
    ("deactivated", "archive", "super_admin"): "archived",
    # Reversible restoration (UC-SA-018 / BW-SA-07)
    ("archived", "restore", "super_admin"): "active",
    # Finalize permanent non-restorable (UC-SA-031 / BW-SA-08)
    ("archived", "window_expire", "system"): "archived_permanent",
}

# (current_state, event, actor) -> resulting_state
ROLE_ASSIGNMENT_TRANSITIONS: dict[tuple[str, str, str], str] = {
    # Immediate assignment (UC-SA-008 / BW-SA-03)
    ("none", "assign_immediate", "super_admin"): "active",
    # Future-dated scheduled assignment (UC-SA-008 / BW-SA-04)
    ("none", "assign_future", "super_admin"): "scheduled",
    # Automatic activation on start date (UC-SA-028 / BW-SA-04)
    ("scheduled", "reach_start_date", "system"): "active",
    # Role validity extension (UC-SA-011 / BW-SA-05)
    ("active", "extend_validity", "super_admin"): "active",
    # Automatic expiry on end date (UC-SA-029 / BW-SA-03..05)
    ("active", "reach_end_date", "system"): "expired",
    # Standard role revocation (UC-SA-010)
    ("active", "revoke_standard", "super_admin"): "revoked",
    # Emergency role revocation (UC-SA-010)
    ("active", "revoke_emergency", "super_admin"): "revoked",
    # Role reassignment (UC-SA-009)
    ("active", "reassign", "super_admin"): "revoked",
}

# (current_state, event, actor) -> resulting_state
PURGE_TRANSITIONS: dict[tuple[str, str, str], str] = {
    # Request permanent purge (UC-SA-022 / BW-SA-01, BW-SA-02)
    ("archived_retention_elapsed", "request_purge", "super_admin"): "pending_it_head",
    # Dual-auth approve (UC-SA-023 / BW-SA-01)
    ("pending_it_head", "approve", "it_head"): "permanently_purged",
    # Dual-auth reject (UC-SA-023 / BW-SA-02)
    ("pending_it_head", "reject", "it_head"): "purge_rejected_retained",
}


def transition_user_state(current_state: str, event: str, actor: str = "super_admin") -> str:
    """Evaluate and transition user lifecycle state. Disallows inexpressible transitions."""
    key = (current_state.lower().strip(), event.lower().strip(), actor.lower().strip())
    if key not in USER_LIFECYCLE_TRANSITIONS:
        msg = f"Illegal user transition from '{current_state}' via '{event}' by '{actor}'."
        raise InvalidStateTransitionError(msg)
    return USER_LIFECYCLE_TRANSITIONS[key]


def transition_role_state(current_state: str, event: str, actor: str = "super_admin") -> str:
    """Evaluate and transition role assignment state."""
    key = (current_state.lower().strip(), event.lower().strip(), actor.lower().strip())
    if key not in ROLE_ASSIGNMENT_TRANSITIONS:
        msg = f"Illegal role transition from '{current_state}' via '{event}' by '{actor}'."
        raise InvalidStateTransitionError(msg)
    return ROLE_ASSIGNMENT_TRANSITIONS[key]


def transition_purge_state(current_state: str, event: str, actor: str) -> str:
    """Evaluate and transition permanent purge state under dual authorization."""
    key = (current_state.lower().strip(), event.lower().strip(), actor.lower().strip())
    if key not in PURGE_TRANSITIONS:
        msg = f"Illegal purge transition from '{current_state}' via '{event}' by '{actor}'."
        raise InvalidStateTransitionError(msg)
    return PURGE_TRANSITIONS[key]
