"""Declarative state machine tables for Super Admin workflows."""

from __future__ import annotations

from dataclasses import dataclass

from modules.superadmin.domain.exceptions import (
    ActorNotAllowedError,
    InvalidTransitionError,
)

# User Account States
USER_ACTIVE = "ACTIVE"
USER_DEACTIVATED = "DEACTIVATED"
USER_ARCHIVED_REVERSIBLE = "ARCHIVED_REVERSIBLE"
USER_ARCHIVED_PERMANENT = "ARCHIVED_PERMANENT"

# User Account Events
EVT_USER_DEACTIVATE = "DEACTIVATE"
EVT_USER_REACTIVATE = "REACTIVATE"
EVT_USER_ARCHIVE = "ARCHIVE"
EVT_USER_RESTORE = "RESTORE"
EVT_USER_EXPIRE_REVERSIBILITY = "EXPIRE_REVERSIBILITY"

# Role Assignment States
ROLE_SCHEDULED = "SCHEDULED"
ROLE_ACTIVE = "ACTIVE"
ROLE_EXTENDED = "EXTENDED"
ROLE_EXPIRED = "EXPIRED"
ROLE_REVOKED = "REVOKED"
ROLE_REASSIGNED = "REASSIGNED"

# Role Assignment Events
EVT_ROLE_ASSIGN_IMMEDIATE = "ASSIGN_IMMEDIATE"
EVT_ROLE_ASSIGN_FUTURE = "ASSIGN_FUTURE"
EVT_ROLE_ACTIVATE_SCHEDULED = "ACTIVATE_SCHEDULED"
EVT_ROLE_EXTEND = "EXTEND"
EVT_ROLE_EXPIRE = "EXPIRE"
EVT_ROLE_REVOKE = "REVOKE"
EVT_ROLE_REASSIGN = "REASSIGN"

# Purge States
PURGE_ELIGIBLE = "ELIGIBLE"
PURGE_PENDING = "PENDING_AUTHORIZATION"
PURGE_AUTHORIZED = "AUTHORIZED"
PURGE_REJECTED = "REJECTED"
PURGE_COMPLETED = "PURGED"

# Actors
ACTOR_SUPERADMIN = "superadmin"
ACTOR_IT_HEAD = "it_head"
ACTOR_SYSTEM = "system"


@dataclass(frozen=True)
class Transition:
    from_state: str
    event: str
    allowed_actors: frozenset[str]
    to_state: str
    guard: str = ""


# User Lifecycle Transitions (BW-SA-06, BW-SA-07, BW-SA-08, CW-SA-03)
USER_TRANSITIONS: list[Transition] = [
    Transition(
        USER_ACTIVE,
        EVT_USER_DEACTIVATE,
        frozenset({ACTOR_SUPERADMIN}),
        USER_DEACTIVATED,
        "pending_work_cleared",
    ),
    Transition(
        USER_DEACTIVATED,
        EVT_USER_REACTIVATE,
        frozenset({ACTOR_SUPERADMIN}),
        USER_ACTIVE,
        "reactivation_justified",
    ),
    Transition(
        USER_DEACTIVATED,
        EVT_USER_ARCHIVE,
        frozenset({ACTOR_SUPERADMIN}),
        USER_ARCHIVED_REVERSIBLE,
        "min_deactivation_interval_met",
    ),
    Transition(
        USER_ARCHIVED_REVERSIBLE,
        EVT_USER_RESTORE,
        frozenset({ACTOR_SUPERADMIN}),
        USER_ACTIVE,
        "within_reversible_window",
    ),
    Transition(
        USER_ARCHIVED_REVERSIBLE,
        EVT_USER_EXPIRE_REVERSIBILITY,
        frozenset({ACTOR_SYSTEM}),
        USER_ARCHIVED_PERMANENT,
        "reversibility_window_elapsed",
    ),
]

# Role Lifecycle Transitions (BW-SA-03, BW-SA-04, BW-SA-05, CW-SA-02)
ROLE_TRANSITIONS: list[Transition] = [
    Transition(
        ROLE_SCHEDULED,
        EVT_ROLE_ACTIVATE_SCHEDULED,
        frozenset({ACTOR_SYSTEM}),
        ROLE_ACTIVE,
        "start_date_reached",
    ),
    Transition(
        ROLE_ACTIVE,
        EVT_ROLE_EXTEND,
        frozenset({ACTOR_SUPERADMIN}),
        ROLE_EXTENDED,
        "before_current_end_date",
    ),
    Transition(
        ROLE_ACTIVE, EVT_ROLE_EXPIRE, frozenset({ACTOR_SYSTEM}), ROLE_EXPIRED, "end_date_reached"
    ),
    Transition(
        ROLE_EXTENDED,
        EVT_ROLE_EXPIRE,
        frozenset({ACTOR_SYSTEM}),
        ROLE_EXPIRED,
        "revised_end_date_reached",
    ),
    Transition(
        ROLE_SCHEDULED,
        EVT_ROLE_REVOKE,
        frozenset({ACTOR_SUPERADMIN, ACTOR_SYSTEM}),
        ROLE_REVOKED,
        "revocation_authorized",
    ),
    Transition(
        ROLE_ACTIVE,
        EVT_ROLE_REVOKE,
        frozenset({ACTOR_SUPERADMIN, ACTOR_SYSTEM}),
        ROLE_REVOKED,
        "revocation_authorized",
    ),
    Transition(
        ROLE_EXTENDED,
        EVT_ROLE_REVOKE,
        frozenset({ACTOR_SUPERADMIN, ACTOR_SYSTEM}),
        ROLE_REVOKED,
        "revocation_authorized",
    ),
    Transition(
        ROLE_ACTIVE,
        EVT_ROLE_REASSIGN,
        frozenset({ACTOR_SUPERADMIN}),
        ROLE_REASSIGNED,
        "handover_completed",
    ),
]


USER_TERMINAL_STATES = frozenset({USER_ARCHIVED_PERMANENT})
ROLE_TERMINAL_STATES = frozenset({ROLE_EXPIRED, ROLE_REVOKED})
PURGE_TERMINAL_STATES = frozenset({"REJECTED", "PURGED"})

PURGE_TRANSITIONS: list[Transition] = [
    Transition(
        "REQUESTED", "AUTHORIZE", frozenset({ACTOR_IT_HEAD}), "AUTHORIZED", "dual_auth_satisfied"
    ),
    Transition("REQUESTED", "REJECT", frozenset({ACTOR_IT_HEAD}), "REJECTED", "rejection_recorded"),
    Transition(
        "AUTHORIZED",
        "EXECUTE_PURGE",
        frozenset({ACTOR_SYSTEM, ACTOR_SUPERADMIN}),
        "PURGED",
        "backup_and_retention_verified",
    ),
]


def is_legal_user_transition(from_state: str, to_state: str) -> bool:
    return any(t.from_state == from_state and t.to_state == to_state for t in USER_TRANSITIONS)


def is_legal_role_transition(from_state: str, to_state: str) -> bool:
    return any(t.from_state == from_state and t.to_state == to_state for t in ROLE_TRANSITIONS)


def is_legal_purge_transition(from_state: str, to_state: str) -> bool:
    return any(t.from_state == from_state and t.to_state == to_state for t in PURGE_TRANSITIONS)


def resolve_user_transition(
    current_state: str, target_or_event: str, actor: str = ACTOR_SUPERADMIN
) -> Transition:
    matching = [
        t
        for t in USER_TRANSITIONS
        if t.from_state == current_state
        and (t.event == target_or_event or t.to_state == target_or_event)
    ]
    if not matching:
        raise InvalidTransitionError(current_state, target_or_event)
    t = matching[0]
    if actor not in t.allowed_actors and ACTOR_SYSTEM not in t.allowed_actors:
        raise ActorNotAllowedError(actor, current_state, t.to_state)
    return t


def resolve_role_transition(
    current_state: str, target_or_event: str, actor: str = ACTOR_SUPERADMIN
) -> Transition:
    matching = [
        t
        for t in ROLE_TRANSITIONS
        if t.from_state == current_state
        and (t.event == target_or_event or t.to_state == target_or_event)
    ]
    if not matching:
        raise InvalidTransitionError(current_state, target_or_event)
    t = matching[0]
    if actor not in t.allowed_actors and ACTOR_SYSTEM not in t.allowed_actors:
        raise ActorNotAllowedError(actor, current_state, t.to_state)
    return t


def resolve_purge_transition(
    current_state: str, target_or_event: str, actor: str = ACTOR_IT_HEAD
) -> Transition:
    matching = [
        t
        for t in PURGE_TRANSITIONS
        if t.from_state == current_state
        and (t.event == target_or_event or t.to_state == target_or_event)
    ]
    if not matching:
        raise InvalidTransitionError(current_state, target_or_event)
    return matching[0]
