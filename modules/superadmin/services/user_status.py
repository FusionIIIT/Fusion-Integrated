"""User activation and deactivation service."""

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.superadmin.domain.exceptions import PolicyConflictError
from modules.superadmin.domain.policy import refuse_self_superadmin_modification
from modules.superadmin.domain.state_machine import (
    ACTOR_SUPERADMIN,
    EVT_USER_DEACTIVATE,
    EVT_USER_REACTIVATE,
    resolve_user_transition,
)
from modules.superadmin.models import (
    RoleAssignmentRecord,
    RoleAssignmentStatus,
    UserAccountRecord,
    UserActivationStatus,
)
from modules.superadmin.services.audit import log_audit_event


@transaction.atomic
def deactivate_user(
    *,
    actor_user_id: int,
    user_id: int,
    reason: str,
    ip_address: str | None = None,
) -> UserAccountRecord:
    # UC-SA-004: Deactivate user account with audit trail and role suspension.
    try:
        refuse_self_superadmin_modification(actor_user_id, user_id, "deactivate")
    except PolicyConflictError as e:
        raise PermissionDeniedError(str(e), code="self_modification_forbidden") from e

    account = UserAccountRecord.objects.select_for_update().filter(user_id=user_id).first()
    if not account:
        raise NotFoundError(f"User with ID {user_id} does not exist.", code="user_not_found")

    # Evaluate state transition.
    resolve_user_transition(account.activation_status, EVT_USER_DEACTIVATE, ACTOR_SUPERADMIN)

    now = timezone.now()
    account.activation_status = UserActivationStatus.DEACTIVATED
    account.deactivation_date = now
    account.deactivation_reason = reason
    account.save(
        update_fields=[
            "activation_status",
            "deactivation_date",
            "deactivation_reason",
            "updated_at",
        ]
    )

    # BR-SA-015: Deactivation automatically revokes/suspends all active held additional roles.
    RoleAssignmentRecord.objects.filter(
        user_id=user_id,
        status__in=[
            RoleAssignmentStatus.ACTIVE,
            RoleAssignmentStatus.SCHEDULED,
            RoleAssignmentStatus.EXTENDED,
        ],
    ).update(status=RoleAssignmentStatus.REVOKED)

    log_audit_event(
        event_type="USER_DEACTIVATED",
        actor_user_id=actor_user_id,
        target_entity="UserAccountRecord",
        target_id=str(user_id),
        ip_address=ip_address,
        action_details={"reason": reason, "deactivated_at": now.isoformat()},
    )
    return account


@transaction.atomic
def reactivate_user(
    *,
    actor_user_id: int,
    user_id: int,
    reason: str,
    ip_address: str | None = None,
) -> UserAccountRecord:
    # UC-SA-005 & BW-SA-06: Reactivate deactivated user account.
    account = UserAccountRecord.objects.select_for_update().filter(user_id=user_id).first()
    if not account:
        raise NotFoundError(f"User with ID {user_id} does not exist.", code="user_not_found")

    if account.activation_status != UserActivationStatus.DEACTIVATED:
        raise ConflictError(
            f"User account is in status {account.activation_status}, "
            "only DEACTIVATED users can be reactivated.",
            code="invalid_user_status",
        )

    resolve_user_transition(account.activation_status, EVT_USER_REACTIVATE, ACTOR_SUPERADMIN)

    account.activation_status = UserActivationStatus.ACTIVE
    account.deactivation_date = None
    account.save(update_fields=["activation_status", "deactivation_date", "updated_at"])

    log_audit_event(
        event_type="USER_REACTIVATED",
        actor_user_id=actor_user_id,
        target_entity="UserAccountRecord",
        target_id=str(user_id),
        ip_address=ip_address,
        action_details={"reason": reason},
    )
    return account
