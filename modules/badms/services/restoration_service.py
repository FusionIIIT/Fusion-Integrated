"""Data restoration workflow service (CFR-BA-011, CW-BA-03)."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from modules.badms.domain.entities import ActorRole, DataClassification, RestorationStatus
from modules.badms.domain.errors import RuleViolation
from modules.badms.domain.rules import (
    check_sensitive_restoration_approval_requirement,
)
from modules.badms.domain.state_machines import resolve_restoration_transition
from modules.badms.models import ArchivalRequest, RestorationRequest
from modules.badms.services.audit_service import record_audit_event
from modules.badms.services.notification_service import queue_notification


@transaction.atomic
def submit_restoration_request(
    *,
    user_id: int,
    username: str,
    archival_request_id: int,
    target_destination: str,
    reason: str,
) -> RestorationRequest:
    """BA-UC-016: User requests restoration of archived data."""
    archive = ArchivalRequest.objects.get(id=archival_request_id)
    classification = archive.authoritative_classification or archive.initial_classification
    is_sensitive = classification == DataClassification.SENSITIVE.value

    target_state = (
        RestorationStatus.PENDING_APPROVAL.value
        if is_sensitive
        else RestorationStatus.REQUESTED_STANDARD.value
    )

    resolve_restoration_transition(
        RestorationStatus.NOT_REQUESTED.value,
        target_state,
        ActorRole.USER,
    )

    restoration = RestorationRequest.objects.create(
        user_id=user_id,
        archival_request=archive,
        classification=classification,
        reason=reason,
        target_destination=target_destination,
        status=target_state,
    )

    record_audit_event(
        actor_id=user_id,
        actor_username=username,
        actor_role="user",
        event_source="user",
        action="restoration_requested",
        resource_type="RestorationRequest",
        resource_id=str(restoration.id),
        outcome="success",
        details={"archive_id": archive.id, "classification": classification},
    )

    queue_notification(
        recipient_id=user_id,
        recipient_role="user",
        notification_type="restoration_request_received",
        subject=f"Restoration Request Received: {archive.file_name}",
        body=f"Your restoration request for '{archive.file_name}' has been recorded.",
    )

    return restoration


@transaction.atomic
def decide_sensitive_restoration_sysadmin(
    *,
    restoration_id: int,
    sysadmin_id: int,
    sysadmin_username: str,
    approve: bool,
    rejection_reason: str = "",
) -> RestorationRequest:
    """BA-UC-017: SysAdmin reviews and decides Sensitive restoration."""
    restoration = RestorationRequest.objects.select_for_update().get(id=restoration_id)

    target_state = RestorationStatus.APPROVED.value if approve else RestorationStatus.REJECTED.value
    resolve_restoration_transition(restoration.status, target_state, ActorRole.SYSADMIN)

    restoration.status = target_state
    restoration.sysadmin_id = sysadmin_id
    restoration.sysadmin_decided_at = timezone.now()
    if not approve:
        if not rejection_reason.strip():
            raise RuleViolation("BW-BA-07", "Rejection reason is required.")
        restoration.rejection_reason = rejection_reason
    restoration.save()

    record_audit_event(
        actor_id=sysadmin_id,
        actor_username=sysadmin_username,
        actor_role="sysadmin",
        event_source="admin",
        action="restoration_approved" if approve else "restoration_rejected",
        resource_type="RestorationRequest",
        resource_id=str(restoration.id),
        outcome="success",
        details={"approve": approve, "rejection_reason": rejection_reason},
    )

    decision_str = "approved" if approve else "rejected"
    queue_notification(
        recipient_id=restoration.user_id,
        recipient_role="user",
        notification_type="restoration_decision",
        subject="Restoration Request Decision",
        body=f"Your sensitive restoration request was {decision_str} by SysAdmin.",
    )

    return restoration


@transaction.atomic
def execute_technical_restoration(
    *,
    restoration_id: int,
    sysadmin_id: int,
    sysadmin_username: str,
) -> RestorationRequest:
    """BA-UC-018: SysAdmin performs technical data restoration."""
    restoration = RestorationRequest.objects.select_for_update().get(id=restoration_id)

    # Check sensitive approval guard
    is_sensitive = restoration.classification == DataClassification.SENSITIVE.value
    check_sensitive_restoration_approval_requirement(
        DataClassification.SENSITIVE if is_sensitive else DataClassification.ROUTINE,
        ActorRole.SYSADMIN,
        is_approved=(restoration.status == RestorationStatus.APPROVED.value),
    )

    resolve_restoration_transition(
        restoration.status,
        RestorationStatus.RESTORED.value,
        ActorRole.SYSADMIN,
    )

    restoration.status = RestorationStatus.RESTORED.value
    restoration.restored_at = timezone.now()
    restoration.save()

    record_audit_event(
        actor_id=sysadmin_id,
        actor_username=sysadmin_username,
        actor_role="sysadmin",
        event_source="admin",
        action="technical_restoration_executed",
        resource_type="RestorationRequest",
        resource_id=str(restoration.id),
        outcome="success",
        details={"destination": restoration.target_destination},
    )

    queue_notification(
        recipient_id=restoration.user_id,
        recipient_role="user",
        notification_type="restoration_completed",
        subject="Data Restored Successfully",
        body=f"Your requested data has been restored to: {restoration.target_destination}.",
    )

    return restoration
