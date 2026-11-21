from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from fusion_auth.principal import Principal
from modules.superadmin.domain.archival_policy import assert_purge_eligible
from modules.superadmin.domain.constants import (
    AUDIT_ACTION_PURGE_APPROVED,
    AUDIT_ACTION_PURGE_EXECUTED,
    AUDIT_ACTION_PURGE_EXPIRED,
    AUDIT_ACTION_PURGE_REJECTED,
    AUDIT_ACTION_PURGE_REQUESTED,
    CONFIG_KEY_PURGE_APPROVAL_TTL_HOURS,
    PURGE_STATUS_EXPIRED,
    PURGE_STATUS_PENDING_IT_HEAD,
)
from modules.superadmin.domain.exceptions import (
    DomainError as PureDomainError,
)
from modules.superadmin.domain.exceptions import (
    SelfApprovalForbiddenError,
)
from modules.superadmin.domain.state_machine import PurgeStateMachine
from modules.superadmin.models.archival import (
    HistoricalDataArchive,
    PurgeRequest,
)
from modules.superadmin.selectors.config import get_active_policy_value
from modules.superadmin.services.audit import record_audit_event


@transaction.atomic
def create_purge_request(
    principal: Principal,
    *,
    archive_id: int,
    request_reason: str,
) -> PurgeRequest:
    archive = HistoricalDataArchive.objects.select_for_update().filter(id=archive_id).first()
    if archive is None:
        raise NotFoundError(f"Historical archive {archive_id} not found.")
    if archive.is_purged:
        raise ConflictError("This archive is already permanently purged.")

    today = timezone.now().date()
    try:
        assert_purge_eligible(archive.retention_expires_at, today)
    except PureDomainError as exc:
        raise DomainError(exc.message, code=exc.code) from exc

    if PurgeRequest.objects.filter(archive=archive, status=PURGE_STATUS_PENDING_IT_HEAD).exists():
        raise ConflictError("A pending purge request already exists for this archive.")

    req = PurgeRequest.objects.create(
        archive=archive,
        status=PURGE_STATUS_PENDING_IT_HEAD,
        requested_by=principal.user_id,
        request_reason=request_reason,
    )

    record_audit_event(
        actor_id=principal.user_id,
        actor_username=principal.username,
        actor_role=principal.active_role or "super_admin",
        action=AUDIT_ACTION_PURGE_REQUESTED,
        target_id=str(req.id),
        target_type="purge_request",
        reason=request_reason,
        context_metadata={"archive_id": archive.id, "category": archive.dataset_category},
    )
    return req


@transaction.atomic
def decide_purge_request(
    principal: Principal,
    *,
    request_id: int,
    approve: bool,
    comments: str = "",
) -> PurgeRequest:
    req = (
        PurgeRequest.objects.select_for_update()
        .select_related("archive")
        .filter(id=request_id)
        .first()
    )
    if req is None:
        raise NotFoundError(f"Purge request {request_id} not found.")

    action = "approve_purge" if approve else "reject_purge"
    actor_role = principal.active_role or ""
    try:
        next_status = PurgeStateMachine.transition(
            req.status,
            action,
            actor_role,
            requester_id=req.requested_by,
            authorizer_id=principal.user_id,
        )
    except SelfApprovalForbiddenError as exc:
        raise ConflictError(exc.message, code="self_approval_forbidden") from exc
    except PureDomainError as exc:
        raise DomainError(exc.message, code=exc.code) from exc

    now = timezone.now()
    req.status = next_status
    req.it_head_id = principal.user_id
    req.it_head_decision_at = now
    req.it_head_comments = comments
    req.save(
        update_fields=[
            "status",
            "it_head_id",
            "it_head_decision_at",
            "it_head_comments",
            "updated_at",
        ]
    )

    audit_action = AUDIT_ACTION_PURGE_APPROVED if approve else AUDIT_ACTION_PURGE_REJECTED
    record_audit_event(
        actor_id=principal.user_id,
        actor_username=principal.username,
        actor_role=principal.active_role or "it_head",
        action=audit_action,
        target_id=str(req.id),
        target_type="purge_request",
        reason=comments,
        context_metadata={"archive_id": req.archive_id, "approved": approve},
    )
    return req


@transaction.atomic
def execute_purge(
    principal: Principal,
    *,
    request_id: int,
    execution_summary: dict[str, Any] | None = None,
) -> PurgeRequest:
    req = (
        PurgeRequest.objects.select_for_update()
        .select_related("archive")
        .filter(id=request_id)
        .first()
    )
    if req is None:
        raise NotFoundError(f"Purge request {request_id} not found.")

    try:
        next_status = PurgeStateMachine.transition(req.status, "execute_purge", "super_admin")
    except PureDomainError as exc:
        raise DomainError(exc.message, code=exc.code) from exc

    now = timezone.now()
    req.status = next_status
    req.purged_at = now
    req.execution_summary = execution_summary or {"records_purged": req.archive.record_count}
    req.save(update_fields=["status", "purged_at", "execution_summary", "updated_at"])

    archive = req.archive
    archive.is_purged = True
    archive.save(update_fields=["is_purged", "updated_at"])

    record_audit_event(
        actor_id=principal.user_id,
        actor_username=principal.username,
        actor_role=principal.active_role or "super_admin",
        action=AUDIT_ACTION_PURGE_EXECUTED,
        target_id=str(req.id),
        target_type="purge_request",
        reason="Physical permanent destruction completed.",
        context_metadata={"archive_id": archive.id, "summary": req.execution_summary},
    )
    return req


@transaction.atomic
def expire_purge_requests_sweep() -> int:
    # Expire pending requests exceeding authorization TTL
    ttl_hours = int(get_active_policy_value(CONFIG_KEY_PURGE_APPROVAL_TTL_HOURS) or 72)
    cutoff = timezone.now() - timedelta(hours=ttl_hours)
    expired_requests = list(
        PurgeRequest.objects.select_for_update().filter(
            status=PURGE_STATUS_PENDING_IT_HEAD, requested_at__lt=cutoff
        )
    )
    count = 0
    for req in expired_requests:
        req.status = PURGE_STATUS_EXPIRED
        req.save(update_fields=["status", "updated_at"])
        count += 1
        record_audit_event(
            actor_id=0,
            actor_username="system_scheduler",
            actor_role="scheduler",
            action=AUDIT_ACTION_PURGE_EXPIRED,
            target_id=str(req.id),
            target_type="purge_request",
            reason=f"Dual authorization TTL ({ttl_hours}h) lapsed without decision.",
        )
    return count
