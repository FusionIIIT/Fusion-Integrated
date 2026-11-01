"""Pure Python finite state machines for System Admin lifecycles.

Covers:
- CW-SA-03 / BW-SA-06, 07, 08: User Deactivation, Archival & Reversibility Window Progression.
- CW-SA-02 / BW-SA-03, 04, 05: Time-Bound Role Assignment, Activation, Extension & Expiry.
- CW-SA-01 / BW-SA-01, 02: Permanent Data Purge Dual Authorization.

Zero Django / DRF imports.
"""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable

from .entities import (
    PurgeRequestStatus,
    RoleAssignmentStatus,
    UserStatus,
)
from .errors import (
    ArchivedUserPermanentError,
    DualAuthorizationRequiredError,
    PurgeRetentionNotElapsedError,
    SystemAdminDomainError,
    UserArchivalIneligibleError,
)


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    guard: Callable[..., bool] | None = None
    effect: str | None = None


# --- 1. User Account Lifecycle State Machine ---
# State progression: ACTIVE -> DEACTIVATED -> ARCHIVED -> RESTORED or PERMANENTLY_ARCHIVED

def guard_user_archival_eligible(
    deactivated_at: datetime | None,
    min_interval_days: int,
    has_pending_transactions: bool,
    current_time: datetime,
) -> bool:
    """BR-SA-004: User must be deactivated for min interval and have no pending transactions."""
    if has_pending_transactions:
        raise UserArchivalIneligibleError("Cannot archive user with pending transactions.")
    if not deactivated_at:
        raise UserArchivalIneligibleError("User has no deactivation timestamp.")
    days_elapsed = (current_time - deactivated_at).total_seconds() / 86400.0
    if days_elapsed < min_interval_days:
        raise UserArchivalIneligibleError(
            f"User must remain deactivated for at least {min_interval_days} days before archival (elapsed: {int(days_elapsed)} days)."
        )
    return True


def guard_archived_user_restorable(
    archived_at: datetime | None,
    reversible_window_days: int,
    is_permanently_archived: bool,
    current_time: datetime,
) -> bool:
    """BR-SA-005, ISS-SA-004: Restoration permitted ONLY inside reversible window."""
    if is_permanently_archived:
        raise ArchivedUserPermanentError(
            "Account is permanently archived and non-restorable. Reversible period has expired."
        )
    if not archived_at:
        raise ArchivedUserPermanentError("Archival timestamp missing.")
    days_elapsed = (current_time - archived_at).total_seconds() / 86400.0
    if days_elapsed > reversible_window_days:
        raise ArchivedUserPermanentError(
            f"Reversible window ({reversible_window_days} days) has expired (elapsed: {int(days_elapsed)} days). Account is permanently non-restorable."
        )
    return True


def validate_user_transition(
    current_status: UserStatus,
    target_status: UserStatus,
    *,
    deactivated_at: datetime | None = None,
    min_interval_days: int = 30,
    has_pending_transactions: bool = False,
    archived_at: datetime | None = None,
    reversible_window_days: int = 180,
    is_permanently_archived: bool = False,
    current_time: datetime | None = None,
) -> None:
    now = current_time or datetime.now()

    if current_status == UserStatus.ACTIVE:
        if target_status == UserStatus.DEACTIVATED:
            return
        raise SystemAdminDomainError(f"Cannot transition active user directly to {target_status}.")

    if current_status == UserStatus.DEACTIVATED:
        if target_status == UserStatus.ACTIVE:
            # Reactivation (BW-SA-06)
            return
        if target_status == UserStatus.ARCHIVED:
            # User Archival (BW-SA-07/08)
            guard_user_archival_eligible(
                deactivated_at, min_interval_days, has_pending_transactions, now
            )
            return
        raise SystemAdminDomainError(f"Cannot transition deactivated user to {target_status}.")

    if current_status == UserStatus.ARCHIVED:
        if target_status == UserStatus.ACTIVE:
            # Reversible Restoration (BW-SA-07)
            guard_archived_user_restorable(
                archived_at, reversible_window_days, is_permanently_archived, now
            )
            return
        raise SystemAdminDomainError(f"Cannot transition archived user directly to {target_status}.")

    raise SystemAdminDomainError(f"Unknown status transition: {current_status} -> {target_status}")


# --- 2. Role Assignment Lifecycle State Machine ---
# State progression: SCHEDULED -> ACTIVE -> EXPIRED / REVOKED / REASSIGNED

def validate_role_assignment_transition(
    current_status: RoleAssignmentStatus,
    target_status: RoleAssignmentStatus,
    *,
    start_date: date,
    end_date: date | None = None,
    today: date | None = None,
) -> None:
    current_date = today or date.today()

    if current_status == RoleAssignmentStatus.SCHEDULED:
        if target_status == RoleAssignmentStatus.ACTIVE:
            if current_date < start_date:
                raise SystemAdminDomainError(
                    f"Scheduled assignment cannot activate before start date ({start_date})."
                )
            return
        if target_status == RoleAssignmentStatus.REVOKED:
            return  # Cancel before starting
        raise SystemAdminDomainError(f"Cannot transition scheduled role to {target_status}.")

    if current_status == RoleAssignmentStatus.ACTIVE:
        if target_status in (
            RoleAssignmentStatus.EXPIRED,
            RoleAssignmentStatus.REVOKED,
            RoleAssignmentStatus.REASSIGNED,
        ):
            return
        raise SystemAdminDomainError(f"Cannot transition active role to {target_status}.")

    if current_status in (
        RoleAssignmentStatus.EXPIRED,
        RoleAssignmentStatus.REVOKED,
        RoleAssignmentStatus.REASSIGNED,
    ):
        raise SystemAdminDomainError(
            f"Terminal role state {current_status} cannot be transitioned."
        )


# --- 3. Permanent Data Purge Lifecycle State Machine ---
# State progression: PENDING_IT_HEAD -> APPROVED (Permanently Purged) or REJECTED

def validate_purge_request(
    retention_until: date,
    current_date: date,
    is_audit_log: bool = False,
) -> None:
    """BR-SA-021: Purge eligible only after retention period has elapsed."""
    if is_audit_log:
        raise SystemAdminDomainError("Audit logs are permanently retained and cannot be purged.")
    if current_date <= retention_until:
        raise PurgeRetentionNotElapsedError(
            f"Retention period has not elapsed (retained until {retention_until}, current date {current_date})."
        )


def validate_purge_authorization(
    status: PurgeRequestStatus,
    it_head_authorized: bool,
    decision: str,  # approve | reject
) -> PurgeRequestStatus:
    """BR-SA-022: Dual authorization by Super Admin and IT Head."""
    if status != PurgeRequestStatus.PENDING_IT_HEAD:
        raise SystemAdminDomainError(
            f"Purge request is not in pending authorization state (current: {status})."
        )
    if not it_head_authorized:
        raise DualAuthorizationRequiredError(
            "Purge authorization must be provided by the IT Head."
        )
    if decision == "approve":
        return PurgeRequestStatus.APPROVED
    if decision == "reject":
        return PurgeRequestStatus.REJECTED
    raise SystemAdminDomainError(f"Invalid purge authorization decision: {decision}")
