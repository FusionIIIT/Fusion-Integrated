"""User archival and reversibility lifecycle service (BW-SA-08, BW-SA-07)."""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.superadmin.domain.policy import (
    is_archived_user_restorable,
    is_user_eligible_for_archival,
)
from modules.superadmin.domain.state_machine import (
    ACTOR_SUPERADMIN,
    ACTOR_SYSTEM,
    EVT_USER_ARCHIVE,
    EVT_USER_EXPIRE_REVERSIBILITY,
    EVT_USER_RESTORE,
    resolve_user_transition,
)
from modules.superadmin.models import UserAccountRecord, UserActivationStatus
from modules.superadmin.selectors.system_config import get_parameter_value
from modules.superadmin.services.audit import log_audit_event


@transaction.atomic
def archive_user(
    *,
    actor_user_id: int,
    user_id: int,
    reason: str,
    ip_address: str | None = None,
) -> UserAccountRecord:
    # UC-SA-015 & BW-SA-08 Transition 1: Archive eligible deactivated user.
    account = UserAccountRecord.objects.select_for_update().filter(user_id=user_id).first()
    if not account:
        raise NotFoundError(f"User with ID {user_id} does not exist.", code="user_not_found")

    now = timezone.now()
    min_days = int(get_parameter_value("MIN_DEACTIVATION_ARCHIVE_DAYS", 30))
    eligible, err_msg = is_user_eligible_for_archival(
        account.deactivation_date, now, min_interval_days=min_days
    )
    if not eligible:
        raise ConflictError(err_msg, code="archival_ineligible")

    resolve_user_transition(account.activation_status, EVT_USER_ARCHIVE, ACTOR_SUPERADMIN)

    reversibility_days = int(get_parameter_value("REVERSIBILITY_WINDOW_DAYS", 90))
    account.activation_status = UserActivationStatus.ARCHIVED_REVERSIBLE
    account.archival_date = now
    account.reversibility_expires_at = now + timedelta(days=reversibility_days)
    account.archival_reason = reason
    account.save(
        update_fields=[
            "activation_status",
            "archival_date",
            "reversibility_expires_at",
            "archival_reason",
            "updated_at",
        ]
    )

    log_audit_event(
        event_type="USER_ARCHIVED",
        actor_user_id=actor_user_id,
        target_entity="UserAccountRecord",
        target_id=str(user_id),
        ip_address=ip_address,
        action_details={
            "reason": reason,
            "reversibility_expires_at": account.reversibility_expires_at.isoformat(),
        },
    )
    return account


def restore_archived_user(
    *,
    actor_user_id: int,
    user_id: int,
    reason: str,
    ip_address: str | None = None,
) -> UserAccountRecord:
    # UC-SA-018 & BW-SA-07: Restore archived user within reversibility window.
    # Note: DEF-SA-01 fix: status update on window expiration is committed before raising conflict.
    with transaction.atomic():
        account = UserAccountRecord.objects.select_for_update().filter(user_id=user_id).first()
        if not account:
            raise NotFoundError(f"User with ID {user_id} does not exist.", code="user_not_found")

        if account.activation_status == UserActivationStatus.ARCHIVED_PERMANENT:
            raise ConflictError(
                "Archived user account is permanently non-restorable.",
                code="permanently_non_restorable",
            )

        if account.activation_status != UserActivationStatus.ARCHIVED_REVERSIBLE:
            raise ConflictError(
                f"User is in status {account.activation_status}; "
                "only ARCHIVED_REVERSIBLE accounts can be restored.",
                code="invalid_archival_status",
            )

        now = timezone.now()
        restorable, err_msg = is_archived_user_restorable(account.reversibility_expires_at, now)
        if not restorable:
            # DEF-SA-01: Commit transition to ARCHIVED_PERMANENT before raising
            account.activation_status = UserActivationStatus.ARCHIVED_PERMANENT
            account.save(update_fields=["activation_status", "updated_at"])
            log_audit_event(
                event_type="USER_ARCHIVAL_PERMANENT_FINALIZED",
                actor_user_id=actor_user_id,
                target_entity="UserAccountRecord",
                target_id=str(user_id),
                ip_address=ip_address,
                action_details={
                    "reason": "Reversibility window expired during restoration attempt."
                },
            )
            raise ConflictError(err_msg, code="reversibility_window_expired")

        resolve_user_transition(account.activation_status, EVT_USER_RESTORE, ACTOR_SUPERADMIN)

        account.activation_status = UserActivationStatus.ACTIVE
        account.archival_date = None
        account.reversibility_expires_at = None
        account.save(
            update_fields=[
                "activation_status",
                "archival_date",
                "reversibility_expires_at",
                "updated_at",
            ]
        )

        log_audit_event(
            event_type="USER_RESTORED",
            actor_user_id=actor_user_id,
            target_entity="UserAccountRecord",
            target_id=str(user_id),
            ip_address=ip_address,
            action_details={"reason": reason},
        )
        return account


@transaction.atomic
def finalize_reversibility_expiry(limit: int = 100) -> int:
    # UC-SA-031 & BW-SA-08 Transition 2: Scheduled task sweeps expired reversible accounts.
    now = timezone.now()
    expired_accounts = UserAccountRecord.objects.select_for_update().filter(
        activation_status=UserActivationStatus.ARCHIVED_REVERSIBLE,
        reversibility_expires_at__lt=now,
    )[:limit]
    count = 0
    for account in expired_accounts:
        resolve_user_transition(
            account.activation_status, EVT_USER_EXPIRE_REVERSIBILITY, ACTOR_SYSTEM
        )
        account.activation_status = UserActivationStatus.ARCHIVED_PERMANENT
        account.save(update_fields=["activation_status", "updated_at"])
        log_audit_event(
            event_type="USER_ARCHIVAL_PERMANENT_FINALIZED",
            actor_user_id=0,
            target_entity="UserAccountRecord",
            target_id=str(account.user_id),
            action_details={
                "reversibility_expired_at": account.reversibility_expires_at.isoformat()
            },
        )
        count += 1
    return count
