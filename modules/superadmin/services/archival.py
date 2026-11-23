from __future__ import annotations

from typing import Any

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from fusion_auth.principal import Principal
from modules.superadmin.domain.archival_policy import (
    assess_user_archival_eligibility,
    calculate_reversible_deadline,
)
from modules.superadmin.domain.constants import (
    ARCHIVAL_STATUS_FINALIZED_PERMANENT,
    ARCHIVAL_STATUS_REVERSIBLE,
    AUDIT_ACTION_USER_ARCHIVED,
    AUDIT_ACTION_USER_FINALIZED,
    AUDIT_ACTION_USER_RESTORED,
    CONFIG_KEY_REVERSIBILITY_WINDOW_DAYS,
)
from modules.superadmin.domain.exceptions import (
    DomainError as PureDomainError,
)
from modules.superadmin.domain.exceptions import (
    InvalidStateTransitionError,
    ReversibilityExpiredError,
)
from modules.superadmin.domain.state_machine import ArchivalStateMachine
from modules.superadmin.domain.validators import (
    validate_institute_email,
    validate_institute_id,
)
from modules.superadmin.models.archival import ArchivedUserRecord
from modules.superadmin.selectors.config import get_active_policy_value
from modules.superadmin.services.audit import record_audit_event
from modules.superadmin.services.notifications import queue_notification


def _validate_and_check_archival_eligibility(
    *,
    user_id: int,
    institute_id: str,
    email: str,
    is_deactivated: bool,
    deactivated_at: timezone.datetime | None,
    has_pending_transactions: bool,
    now: timezone.datetime,
) -> None:
    try:
        validate_institute_id(institute_id)
        validate_institute_email(email)
    except PureDomainError as exc:
        raise DomainError(exc.message, code=exc.code) from exc

    if ArchivedUserRecord.objects.filter(user_id=user_id).exists():
        raise ConflictError("This user is already archived.", code="user_already_archived")

    verdict = assess_user_archival_eligibility(
        is_deactivated=is_deactivated,
        deactivated_at=deactivated_at,
        has_pending_transactions=has_pending_transactions,
        min_deactivation_days=30,
        now=now,
    )
    if not verdict.is_eligible:
        raise DomainError(verdict.reason, code="archival_ineligible")


def _emit_user_archived_effects(
    principal: Principal,
    *,
    user_id: int,
    institute_id: str,
    username: str,
    email: str,
    archival_reason: str,
    reversible_until: timezone.datetime,
) -> None:
    record_audit_event(
        actor_id=principal.user_id,
        actor_username=principal.username,
        actor_role=principal.active_role or "super_admin",
        action=AUDIT_ACTION_USER_ARCHIVED,
        target_id=str(user_id),
        target_type="user",
        reason=archival_reason,
        context_metadata={
            "institute_id": institute_id,
            "reversible_until": reversible_until.isoformat(),
        },
    )
    queue_notification(
        recipient_id=user_id,
        recipient_email=email,
        template_code="user_archived",
        subject="Notice: Your IIITDMJ Account Has Been Placed in Archival",
        body=(
            f"Your account ({username}) was archived. "
            f"Restoration is possible until {reversible_until.date()}."
        ),
    )


@transaction.atomic
def archive_user(
    principal: Principal,
    *,
    user_id: int,
    institute_id: str,
    username: str,
    email: str,
    user_kind: str,
    is_deactivated: bool,
    deactivated_at: timezone.datetime | None = None,
    has_pending_transactions: bool,
    archival_reason: str,
    metadata_snapshot: dict[str, Any] | None = None,
) -> ArchivedUserRecord:
    now = timezone.now()
    _validate_and_check_archival_eligibility(
        user_id=user_id,
        institute_id=institute_id,
        email=email,
        is_deactivated=is_deactivated,
        deactivated_at=deactivated_at,
        has_pending_transactions=has_pending_transactions,
        now=now,
    )
    window_days = int(get_active_policy_value(CONFIG_KEY_REVERSIBILITY_WINDOW_DAYS) or 30)
    reversible_until = calculate_reversible_deadline(now, window_days)
    record = ArchivedUserRecord.objects.create(
        user_id=user_id,
        institute_id=institute_id,
        username=username,
        email=email,
        user_kind=user_kind,
        status=ARCHIVAL_STATUS_REVERSIBLE,
        archived_at=now,
        reversible_until=reversible_until,
        authorized_by=principal.user_id,
        archival_reason=archival_reason,
        metadata_snapshot=metadata_snapshot or {},
    )
    _emit_user_archived_effects(
        principal,
        user_id=user_id,
        institute_id=institute_id,
        username=username,
        email=email,
        archival_reason=archival_reason,
        reversible_until=reversible_until,
    )
    return record


@transaction.atomic
def restore_archived_user(
    principal: Principal,
    *,
    user_id: int,
    restoration_reason: str,
) -> ArchivedUserRecord:
    record = ArchivedUserRecord.objects.select_for_update().filter(user_id=user_id).first()
    if record is None:
        raise NotFoundError(f"Archived user {user_id} not found.")

    now = timezone.now()
    try:
        next_status = ArchivalStateMachine.transition(
            record.status,
            "restore",
            "super_admin",
            reversible_until=record.reversible_until,
            now=now,
        )
    except ReversibilityExpiredError as exc:
        raise ConflictError(exc.message, code="reversibility_expired") from exc
    except InvalidStateTransitionError as exc:
        raise ConflictError(exc.message, code=exc.code) from exc
    except PureDomainError as exc:
        raise DomainError(exc.message, code=exc.code) from exc

    record.status = next_status
    record.restored_at = now
    record.restored_by = principal.user_id
    record.restoration_reason = restoration_reason
    record.save(
        update_fields=["status", "restored_at", "restored_by", "restoration_reason", "updated_at"]
    )

    record_audit_event(
        actor_id=principal.user_id,
        actor_username=principal.username,
        actor_role=principal.active_role or "super_admin",
        action=AUDIT_ACTION_USER_RESTORED,
        target_id=str(user_id),
        target_type="user",
        reason=restoration_reason,
    )
    return record


@transaction.atomic
def expire_reversibility_sweep() -> int:
    # Transitions users whose restoration window expired to permanently finalized
    now = timezone.now()
    records = list(
        ArchivedUserRecord.objects.select_for_update().filter(
            status=ARCHIVAL_STATUS_REVERSIBLE, reversible_until__lt=now
        )
    )
    count = 0
    for record in records:
        record.status = ARCHIVAL_STATUS_FINALIZED_PERMANENT
        record.finalized_permanent_at = now
        record.save(update_fields=["status", "finalized_permanent_at", "updated_at"])
        count += 1
        record_audit_event(
            actor_id=0,
            actor_username="system_scheduler",
            actor_role="scheduler",
            action=AUDIT_ACTION_USER_FINALIZED,
            target_id=str(record.user_id),
            target_type="user",
            reason="Reversibility window elapsed automatically per ISS-SA-004.",
        )
    return count
