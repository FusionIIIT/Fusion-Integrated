"""Declarative state machines for BADMS.

Pure Python. Defines legal transitions, permissible actors, and guards for:
- Archival Requests (CW-BA-01, BW-BA-01, BW-BA-02, BW-BA-03)
- Storage Extension Requests (CW-BA-02, BW-BA-04, BW-BA-05)
- Data Restoration Requests (CW-BA-03, BW-BA-06, BW-BA-07)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from modules.badms.domain.entities import (
    ActorRole,
    ArchivalStatus,
    RestorationStatus,
    StorageExtensionStatus,
)
from modules.badms.domain.errors import ActorNotAllowed, InvalidTransition


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    action: str
    allowed_roles: frozenset[ActorRole]
    guards: tuple[str, ...] = field(default_factory=tuple)


# ==============================================================================
# 1. Archival Request State Machine (CW-BA-01, BW-BA-01..03)
# ==============================================================================

ARCHIVAL_TRANSITIONS: tuple[Transition, ...] = (
    # User submission
    Transition(
        frm=ArchivalStatus.NOT_SUBMITTED.value,
        to=ArchivalStatus.SUBMITTED.value,
        action="submit",
        allowed_roles=frozenset({ActorRole.USER, ActorRole.SYSADMIN, ActorRole.HOD}),
        guards=("valid_metadata", "quota_checked"),
    ),
    # HoD Rejection (BW-BA-01)
    Transition(
        frm=ArchivalStatus.SUBMITTED.value,
        to=ArchivalStatus.REJECTED.value,
        action="hod_reject",
        allowed_roles=frozenset({ActorRole.HOD}),
        guards=("same_department", "has_rejection_reason"),
    ),
    # HoD Approval (BW-BA-02, BW-BA-03)
    Transition(
        frm=ArchivalStatus.SUBMITTED.value,
        to=ArchivalStatus.HOD_APPROVED.value,
        action="hod_approve",
        allowed_roles=frozenset({ActorRole.HOD}),
        guards=("same_department",),
    ),
    # SysAdmin Authoritative Classification -> Non-Sensitive (BW-BA-02)
    Transition(
        frm=ArchivalStatus.HOD_APPROVED.value,
        to=ArchivalStatus.CLASSIFIED_NON_SENSITIVE.value,
        action="sysadmin_classify_non_sensitive",
        allowed_roles=frozenset({ActorRole.SYSADMIN}),
        guards=("is_non_sensitive", "policy_applied"),
    ),
    # SysAdmin Authoritative Classification -> Sensitive (BW-BA-03)
    Transition(
        frm=ArchivalStatus.HOD_APPROVED.value,
        to=ArchivalStatus.CLASSIFIED_SENSITIVE.value,
        action="sysadmin_classify_sensitive",
        allowed_roles=frozenset({ActorRole.SYSADMIN}),
        guards=("is_sensitive", "route_to_it_sec"),
    ),
    # IT Security Encryption & Archive Creation (BW-BA-03)
    Transition(
        frm=ArchivalStatus.CLASSIFIED_SENSITIVE.value,
        to=ArchivalStatus.SENSITIVE_ARCHIVE_ENCRYPTED.value,
        action="it_sec_encrypt",
        allowed_roles=frozenset({ActorRole.IT_SECURITY}),
        guards=("aes_256_configured", "encryption_succeeds"),
    ),
)

_ARCHIVAL_INDEX: dict[tuple[str, str], Transition] = {
    (t.frm, t.to): t for t in ARCHIVAL_TRANSITIONS
}


def resolve_archival_transition(
    frm: str, to: str, actor_role: ActorRole | None = None
) -> Transition:
    t = _ARCHIVAL_INDEX.get((frm, to))
    if t is None:
        raise InvalidTransition("ArchivalRequest", frm, to)
    if actor_role is not None and actor_role not in t.allowed_roles:
        raise ActorNotAllowed(str(actor_role.value), f"transition from {frm} to {to}")
    return t


# ==============================================================================
# 2. Storage Extension State Machine (CW-BA-02, BW-BA-04..05)
# ==============================================================================

EXTENSION_TRANSITIONS: tuple[Transition, ...] = (
    # User submission (AFR-BA-045)
    Transition(
        frm=StorageExtensionStatus.NOT_SUBMITTED.value,
        to=StorageExtensionStatus.SUBMITTED.value,
        action="submit_extension",
        allowed_roles=frozenset({ActorRole.USER, ActorRole.SYSADMIN, ActorRole.HOD}),
        guards=("quota_full", "infrastructure_checked"),
    ),
    # HoD Rejection (BW-BA-04)
    Transition(
        frm=StorageExtensionStatus.SUBMITTED.value,
        to=StorageExtensionStatus.REJECTED.value,
        action="hod_reject_extension",
        allowed_roles=frozenset({ActorRole.HOD}),
        guards=("same_department", "has_rejection_reason"),
    ),
    # HoD Approval (BW-BA-05)
    Transition(
        frm=StorageExtensionStatus.SUBMITTED.value,
        to=StorageExtensionStatus.APPROVED.value,
        action="hod_approve_extension",
        allowed_roles=frozenset({ActorRole.HOD}),
        guards=("same_department",),
    ),
)

_EXTENSION_INDEX: dict[tuple[str, str], Transition] = {
    (t.frm, t.to): t for t in EXTENSION_TRANSITIONS
}


def resolve_extension_transition(
    frm: str, to: str, actor_role: ActorRole | None = None
) -> Transition:
    t = _EXTENSION_INDEX.get((frm, to))
    if t is None:
        raise InvalidTransition("StorageExtensionRequest", frm, to)
    if actor_role is not None and actor_role not in t.allowed_roles:
        raise ActorNotAllowed(str(actor_role.value), f"transition from {frm} to {to}")
    return t


# ==============================================================================
# 3. Data Restoration State Machine (CW-BA-03, BW-BA-06..07)
# ==============================================================================

RESTORATION_TRANSITIONS: tuple[Transition, ...] = (
    # Standard non-sensitive restoration intake (BW-BA-06)
    Transition(
        frm=RestorationStatus.NOT_REQUESTED.value,
        to=RestorationStatus.REQUESTED_STANDARD.value,
        action="request_restore_standard",
        allowed_roles=frozenset({ActorRole.USER, ActorRole.SYSADMIN, ActorRole.HOD}),
        guards=("is_non_sensitive",),
    ),
    # Sensitive restoration intake (BW-BA-07)
    Transition(
        frm=RestorationStatus.NOT_REQUESTED.value,
        to=RestorationStatus.PENDING_APPROVAL.value,
        action="request_restore_sensitive",
        allowed_roles=frozenset({ActorRole.USER, ActorRole.SYSADMIN, ActorRole.HOD}),
        guards=("is_sensitive", "sysadmin_approval_required"),
    ),
    # SysAdmin Rejection of Sensitive Restoration (BW-BA-07)
    Transition(
        frm=RestorationStatus.PENDING_APPROVAL.value,
        to=RestorationStatus.REJECTED.value,
        action="sysadmin_reject",
        allowed_roles=frozenset({ActorRole.SYSADMIN}),
        guards=("has_rejection_reason",),
    ),
    # SysAdmin Approval of Sensitive Restoration (BW-BA-07)
    Transition(
        frm=RestorationStatus.PENDING_APPROVAL.value,
        to=RestorationStatus.APPROVED.value,
        action="sysadmin_approve",
        allowed_roles=frozenset({ActorRole.SYSADMIN}),
        guards=(),
    ),
    # Standard restoration technical execution (BW-BA-06)
    Transition(
        frm=RestorationStatus.REQUESTED_STANDARD.value,
        to=RestorationStatus.RESTORED.value,
        action="execute_restore_standard",
        allowed_roles=frozenset({ActorRole.SYSADMIN}),
        guards=("execution_succeeds",),
    ),
    # Approved sensitive restoration technical execution (BW-BA-07)
    Transition(
        frm=RestorationStatus.APPROVED.value,
        to=RestorationStatus.RESTORED.value,
        action="execute_restore_sensitive",
        allowed_roles=frozenset({ActorRole.SYSADMIN}),
        guards=("execution_succeeds",),
    ),
)

_RESTORATION_INDEX: dict[tuple[str, str], Transition] = {
    (t.frm, t.to): t for t in RESTORATION_TRANSITIONS
}


def resolve_restoration_transition(
    frm: str, to: str, actor_role: ActorRole | None = None
) -> Transition:
    t = _RESTORATION_INDEX.get((frm, to))
    if t is None:
        raise InvalidTransition("RestorationRequest", frm, to)
    if actor_role is not None and actor_role not in t.allowed_roles:
        raise ActorNotAllowed(str(actor_role.value), f"transition from {frm} to {to}")
    return t
