"""Storage quota and extension service (CFR-BA-012, CFR-BA-013, CW-BA-02)."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from modules.badms.domain.entities import ActorRole, StorageExtensionStatus
from modules.badms.domain.errors import RuleViolation
from modules.badms.domain.rules import (
    check_hod_department_scope,
    validate_infrastructure_capacity,
    validate_storage_extension_eligibility,
)
from modules.badms.domain.state_machines import resolve_extension_transition
from modules.badms.models import StorageExtensionRequest, UserStorageQuota
from modules.badms.services.audit_service import record_audit_event
from modules.badms.services.notification_service import queue_notification


@transaction.atomic
def submit_storage_extension(
    *,
    user_id: int,
    username: str,
    department_id: int,
    requested_bytes: int,
    justification: str,
    attachment_path: str = "",
) -> StorageExtensionRequest:
    """BA-UC-007: User submits storage extension when quota is full."""
    quota, _ = UserStorageQuota.objects.get_or_create(
        user_id=user_id,
        defaults={
            "department_id": department_id,
            "used_bytes": 10737418240,
            "quota_bytes": 10737418240,
            "is_full": True,
        },
    )

    # BR-BA-016: Quota must be full
    validate_storage_extension_eligibility(quota.used_bytes, quota.quota_bytes)

    # AFR-BA-052: Infrastructure sufficiency
    validate_infrastructure_capacity(requested_bytes, quota.available_infra_bytes)

    resolve_extension_transition(
        StorageExtensionStatus.NOT_SUBMITTED.value,
        StorageExtensionStatus.SUBMITTED.value,
        ActorRole.USER,
    )

    request = StorageExtensionRequest.objects.create(
        user_id=user_id,
        department_id=department_id,
        requested_bytes=requested_bytes,
        current_usage_bytes=quota.used_bytes,
        current_quota_bytes=quota.quota_bytes,
        justification=justification,
        attachment_path=attachment_path,
        status=StorageExtensionStatus.SUBMITTED.value,
    )

    record_audit_event(
        actor_id=user_id,
        actor_username=username,
        actor_role="user",
        event_source="user",
        action="storage_extension_submitted",
        resource_type="StorageExtensionRequest",
        resource_id=str(request.id),
        department_id=department_id,
        outcome="success",
        details={"requested_bytes": requested_bytes},
    )

    queue_notification(
        recipient_id=user_id,
        recipient_role="user",
        notification_type="storage_extension_submitted",
        subject="Storage Extension Request Submitted",
        body=(
            f"Your extension request for {requested_bytes} bytes was submitted "
            "and routed to your HoD."
        ),
    )

    return request


@transaction.atomic
def decide_storage_extension_hod(
    *,
    request_id: int,
    hod_id: int,
    hod_username: str,
    hod_department_id: int,
    approve: bool,
    rejection_reason: str = "",
) -> StorageExtensionRequest:
    """BA-UC-008: HoD reviews and approves/rejects extension for their department."""
    request = StorageExtensionRequest.objects.select_for_update().get(id=request_id)
    check_hod_department_scope(ActorRole.HOD, hod_department_id, request.department_id)

    target_state = (
        StorageExtensionStatus.APPROVED.value if approve else StorageExtensionStatus.REJECTED.value
    )
    resolve_extension_transition(request.status, target_state, ActorRole.HOD)

    request.status = target_state
    request.hod_id = hod_id
    request.hod_decided_at = timezone.now()
    if not approve:
        if not rejection_reason.strip():
            raise RuleViolation("BW-BA-04", "Rejection reason is required.")
        request.rejection_reason = rejection_reason
    else:
        # Update user's quota on approval
        quota = UserStorageQuota.objects.filter(user_id=request.user_id).first()
        if quota:
            quota.quota_bytes += request.requested_bytes
            quota.is_full = quota.used_bytes >= quota.quota_bytes
            quota.save()

    request.save()

    record_audit_event(
        actor_id=hod_id,
        actor_username=hod_username,
        actor_role="hod",
        event_source="admin",
        action="storage_extension_approved" if approve else "storage_extension_rejected",
        resource_type="StorageExtensionRequest",
        resource_id=str(request.id),
        department_id=request.department_id,
        outcome="success",
        details={"approve": approve, "rejection_reason": rejection_reason},
    )

    decision_str = "approved" if approve else "rejected"
    queue_notification(
        recipient_id=request.user_id,
        recipient_role="user",
        notification_type="storage_extension_decision",
        subject="Storage Extension Decision",
        body=f"Your storage extension request was {decision_str} by your HoD.",
    )

    return request


def evaluate_all_storage_thresholds() -> int:
    """BA-UC-022: Monitor storage thresholds for all users."""
    updated = 0
    for quota in UserStorageQuota.objects.all():
        is_now_full = quota.used_bytes >= quota.quota_bytes
        if quota.is_full != is_now_full:
            quota.is_full = is_now_full
            quota.save(update_fields=["is_full", "updated_at"])
            updated += 1
    return updated
