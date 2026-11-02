"""Declarative state-transition models for modules.system_admin.

Pure Python implementation of:
  - Role Validity State Machine (CW-SA-02, BW-SA-03..05, UC-SA-010..011, UC-SA-028..029)
  - User Deactivation & Archive Lifecycle (CW-SA-03, BW-SA-06..08, UC-SA-005, UC-SA-015, UC-SA-018, UC-SA-031)
  - Permanent Data Purge Authorization (CW-SA-01, BW-SA-01..02, UC-SA-022..023)

Free of external dependencies (strictly NO Django, DRF, or Celery).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional, FrozenSet

from .dataclasses import ArchivalEligibilityVerdict
from .exceptions import InvalidStateTransitionError

# -----------------------------------------------------------------------------
# Role Validity States & State Machine (CW-SA-02)
# -----------------------------------------------------------------------------
ROLE_SCHEDULED = "scheduled"
ROLE_ACTIVE = "active"
ROLE_EXTENDED = "extended"
ROLE_EXPIRED = "expired"
ROLE_REVOKED = "revoked"

ROLE_TERMINAL_STATES: FrozenSet[str] = frozenset({ROLE_EXPIRED, ROLE_REVOKED})
ALL_ROLE_STATES: FrozenSet[str] = frozenset({
    ROLE_SCHEDULED,
    ROLE_ACTIVE,
    ROLE_EXTENDED,
    ROLE_EXPIRED,
    ROLE_REVOKED,
})


class RoleStateMachine:
    """Manages role validity transitions (CW-SA-02)."""

    @staticmethod
    def validate_immediate_assignment(start_date: date, today: date) -> str:
        """BW-SA-03: Immediate activation if start_date <= today, else scheduled."""
        if start_date <= today:
            return ROLE_ACTIVE
        return ROLE_SCHEDULED

    @staticmethod
    def can_activate(current_state: str, start_date: date, today: date) -> bool:
        """BW-SA-04 / UC-SA-028: Scheduled -> Active when start_date <= today."""
        return current_state == ROLE_SCHEDULED and today >= start_date

    @staticmethod
    def can_extend(
        current_state: str,
        current_end_date: date,
        new_end_date: date,
        today: date,
    ) -> bool:
        """BW-SA-05 / UC-SA-011: Active/Extended -> Extended if new_end_date > current_end_date and not expired."""
        if current_state not in {ROLE_ACTIVE, ROLE_EXTENDED}:
            return False
        if today > current_end_date:
            return False   # Cannot extend an already expired role
        return new_end_date > current_end_date

    @staticmethod
    def can_expire(current_state: str, end_date: Optional[date], today: date) -> bool:
        """UC-SA-029: Active/Extended -> Expired when today >= end_date."""
        if current_state not in {ROLE_ACTIVE, ROLE_EXTENDED}:
            return False
        if end_date is None:
            return False   # Indefinite role does not expire automatically
        return today >= end_date

    @staticmethod
    def can_revoke(current_state: str) -> bool:
        """UC-SA-010: Scheduled, Active, or Extended may be revoked."""
        return current_state in {ROLE_SCHEDULED, ROLE_ACTIVE, ROLE_EXTENDED}


# -----------------------------------------------------------------------------
# User Lifecycle States & State Machine (CW-SA-03)
# -----------------------------------------------------------------------------
USER_ACTIVE = "active"
USER_DEACTIVATED = "deactivated"
USER_ARCHIVED_REVERSIBLE = "archived_reversible"
USER_ARCHIVED_PERMANENT = "archived_permanent"

ALL_USER_STATES: FrozenSet[str] = frozenset({
    USER_ACTIVE,
    USER_DEACTIVATED,
    USER_ARCHIVED_REVERSIBLE,
    USER_ARCHIVED_PERMANENT,
})


class UserLifecycleStateMachine:
    """Manages deactivated user resolution and archival (CW-SA-03)."""

    @staticmethod
    def can_deactivate(current_state: str) -> bool:
        """Active -> Deactivated."""
        return current_state == USER_ACTIVE

    @staticmethod
    def can_reactivate(current_state: str) -> bool:
        """BW-SA-06 / UC-SA-005: Deactivated -> Active."""
        return current_state == USER_DEACTIVATED

    @staticmethod
    def can_archive(current_state: str, eligibility: ArchivalEligibilityVerdict) -> bool:
        """UC-SA-015: Deactivated -> Archived Reversible if eligibility satisfied."""
        return current_state == USER_DEACTIVATED and eligibility.is_eligible

    @staticmethod
    def can_restore_from_archive(
        current_state: str,
        reversible_until: datetime,
        now: datetime,
    ) -> bool:
        """BW-SA-07 / UC-SA-018: Restorable only within reversible window (BR-SA-005)."""
        if current_state != USER_ARCHIVED_REVERSIBLE:
            return False
        return now <= reversible_until

    @staticmethod
    def can_finalize_permanent(
        current_state: str,
        reversible_until: datetime,
        now: datetime,
    ) -> bool:
        """BW-SA-08 / UC-SA-031 / ISS-SA-004: Reversible -> Permanent once window expires."""
        if current_state != USER_ARCHIVED_REVERSIBLE:
            return False
        return now > reversible_until


# -----------------------------------------------------------------------------
# Permanent Data Purge States & State Machine (CW-SA-01)
# -----------------------------------------------------------------------------
PURGE_NOT_REQUESTED = "not_requested"
PURGE_PENDING_IT_HEAD = "pending_it_head"
PURGE_APPROVED = "approved"
PURGE_REJECTED = "rejected"
PURGE_COMPLETED = "permanently_purged"

ALL_PURGE_STATES: FrozenSet[str] = frozenset({
    PURGE_NOT_REQUESTED,
    PURGE_PENDING_IT_HEAD,
    PURGE_APPROVED,
    PURGE_REJECTED,
    PURGE_COMPLETED,
})


class PurgeAuthorizationStateMachine:
    """Dual-authorization state machine for permanent purge (CW-SA-01)."""

    @staticmethod
    def can_request_purge(retention_expired: bool) -> bool:
        """UC-SA-022 / BR-SA-021: Super Admin requests purge after retention period."""
        return retention_expired

    @staticmethod
    def transition_on_decision(current_state: str, it_head_approved: bool) -> str:
        """UC-SA-023 / BR-SA-022: IT Head approves (BW-SA-01) or rejects (BW-SA-02)."""
        if current_state != PURGE_PENDING_IT_HEAD:
            raise InvalidStateTransitionError(current_state, "it_head_decision", "purge_request")
        if it_head_approved:
            return PURGE_APPROVED
        return PURGE_REJECTED
