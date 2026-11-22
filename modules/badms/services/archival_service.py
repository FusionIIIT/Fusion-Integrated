"""Secure archival workflow service (CFR-BA-005..008, CFR-BA-010, CW-BA-01)."""

from __future__ import annotations

import hashlib

from django.db import transaction
from django.utils import timezone

from modules.badms.domain.entities import ActorRole, ArchivalStatus, DataClassification
from modules.badms.domain.errors import RuleViolation
from modules.badms.domain.rules import (
    check_hod_department_scope,
    check_it_security_encryption_auth,
    check_special_archival_auth,
    check_sysadmin_classification_auth,
    resolve_initial_classification,
    validate_retention_classification,
    validate_sensitive_encryption_algorithm,
)
from modules.badms.domain.state_machines import resolve_archival_transition
from modules.badms.models import ArchivalRequest, SpecialArchivalRecord, UserStorageQuota
from modules.badms.services.audit_service import record_audit_event
from modules.badms.services.notification_service import queue_notification


@transaction.atomic
def submit_archival_request(
    *,
    user_id: int,
    username: str,
    department_id: int,
    file_name: str,
    file_type: str,
    file_size_bytes: int,
    owners: str,
    reason: str,
    attachment_path: str,
    initial_classification: str | None = None,
) -> ArchivalRequest:
    """BA-UC-002: User submits secure archival request."""
    # Check quota
    quota = UserStorageQuota.objects.filter(user_id=user_id).first()
    if quota and (quota.used_bytes + file_size_bytes > quota.quota_bytes):
        raise RuleViolation("AFR-BA-021", "Storage quota exceeded for archival submission.")

    classification_enum = resolve_initial_classification(initial_classification)

    # Validate state machine move
    resolve_archival_transition(
        ArchivalStatus.NOT_SUBMITTED.value,
        ArchivalStatus.SUBMITTED.value,
        ActorRole.USER,
    )

    request = ArchivalRequest.objects.create(
        user_id=user_id,
        department_id=department_id,
        file_name=file_name,
        file_type=file_type,
        file_size_bytes=file_size_bytes,
        owners=owners,
        reason=reason,
        attachment_path=attachment_path,
        initial_classification=classification_enum.value,
        status=ArchivalStatus.SUBMITTED.value,
    )

    # Deduct storage quota
    if quota:
        quota.used_bytes += file_size_bytes
        if quota.used_bytes >= quota.quota_bytes:
            quota.is_full = True
        quota.save()

    record_audit_event(
        actor_id=user_id,
        actor_username=username,
        actor_role="user",
        event_source="user",
        action="archival_request_submitted",
        resource_type="ArchivalRequest",
        resource_id=str(request.id),
        department_id=department_id,
        outcome="success",
        details={"file_name": file_name, "file_size_bytes": file_size_bytes},
    )

    queue_notification(
        recipient_id=user_id,
        recipient_role="user",
        notification_type="archival_submission_confirmed",
        subject=f"Archival Request Submitted: {file_name}",
        body=f"Your archival request for '{file_name}' was received and routed to your HoD.",
    )

    return request


@transaction.atomic
def decide_archival_request_hod(
    *,
    request_id: int,
    hod_id: int,
    hod_username: str,
    hod_department_id: int,
    approve: bool,
    rejection_reason: str = "",
) -> ArchivalRequest:
    """BA-UC-003: HoD approves or rejects request for their department."""
    request = ArchivalRequest.objects.select_for_update().get(id=request_id)

    # Enforce department scope
    check_hod_department_scope(ActorRole.HOD, hod_department_id, request.department_id)

    target_state = ArchivalStatus.HOD_APPROVED.value if approve else ArchivalStatus.REJECTED.value
    resolve_archival_transition(request.status, target_state, ActorRole.HOD)

    request.status = target_state
    request.hod_id = hod_id
    request.hod_decided_at = timezone.now()
    if not approve:
        if not rejection_reason.strip():
            raise RuleViolation("BW-BA-01", "Rejection reason is required.")
        request.hod_rejection_reason = rejection_reason
    request.save()

    record_audit_event(
        actor_id=hod_id,
        actor_username=hod_username,
        actor_role="hod",
        event_source="admin",
        action="archival_request_approved" if approve else "archival_request_rejected",
        resource_type="ArchivalRequest",
        resource_id=str(request.id),
        department_id=request.department_id,
        outcome="success",
        details={"approve": approve, "rejection_reason": rejection_reason},
    )

    queue_notification(
        recipient_id=request.user_id,
        recipient_role="user",
        notification_type="archival_decision",
        subject=f"Archival Decision: {request.file_name}",
        body=f"Your request was {'approved' if approve else 'rejected'} by your HoD.",
    )

    return request


@transaction.atomic
def classify_archival_request_sysadmin(
    *,
    request_id: int,
    sysadmin_id: int,
    sysadmin_username: str,
    authoritative_classification: str,
) -> ArchivalRequest:
    """BA-UC-004: SysAdmin assigns authoritative classification."""
    request = ArchivalRequest.objects.select_for_update().get(id=request_id)
    check_sysadmin_classification_auth(ActorRole.SYSADMIN)

    auth_class_enum = DataClassification(authoritative_classification.lower())
    target_state = (
        ArchivalStatus.CLASSIFIED_SENSITIVE.value
        if auth_class_enum == DataClassification.SENSITIVE
        else ArchivalStatus.CLASSIFIED_NON_SENSITIVE.value
    )

    resolve_archival_transition(request.status, target_state, ActorRole.SYSADMIN)

    request.status = target_state
    request.authoritative_classification = auth_class_enum.value
    request.classified_by_id = sysadmin_id
    request.classified_at = timezone.now()
    request.save()

    # Apply retention policy
    retention_tag = validate_retention_classification(auth_class_enum)

    record_audit_event(
        actor_id=sysadmin_id,
        actor_username=sysadmin_username,
        actor_role="sysadmin",
        event_source="admin",
        action="archival_classified",
        resource_type="ArchivalRequest",
        resource_id=str(request.id),
        department_id=request.department_id,
        outcome="success",
        details={"classification": auth_class_enum.value, "retention_tag": retention_tag},
    )

    return request


@transaction.atomic
def configure_sensitive_encryption(
    *,
    request_id: int,
    security_officer_id: int,
    security_officer_username: str,
    encryption_algorithm: str = "AES-256",
) -> ArchivalRequest:
    """BA-UC-005: IT Security configures encryption and creates encrypted archive."""
    request = ArchivalRequest.objects.select_for_update().get(id=request_id)
    check_it_security_encryption_auth(ActorRole.IT_SECURITY)
    validate_sensitive_encryption_algorithm(encryption_algorithm)

    resolve_archival_transition(
        request.status,
        ArchivalStatus.SENSITIVE_ARCHIVE_ENCRYPTED.value,
        ActorRole.IT_SECURITY,
    )

    encrypted_path = f"/var/archives/encrypted/{request.id}_{request.file_name}.enc"
    request.status = ArchivalStatus.SENSITIVE_ARCHIVE_ENCRYPTED.value
    request.security_officer_id = security_officer_id
    request.encryption_algorithm = encryption_algorithm
    request.encrypted_archive_path = encrypted_path
    request.encryption_configured_at = timezone.now()
    request.save()

    record_audit_event(
        actor_id=security_officer_id,
        actor_username=security_officer_username,
        actor_role="it_security",
        event_source="security",
        action="sensitive_encryption_configured",
        resource_type="ArchivalRequest",
        resource_id=str(request.id),
        department_id=request.department_id,
        outcome="success",
        details={"algorithm": encryption_algorithm, "encrypted_path": encrypted_path},
    )

    return request


@transaction.atomic
def execute_special_archival(
    *,
    super_admin_id: int,
    super_admin_username: str,
    dataset_name: str,
    source_authority: str,
    reason: str,
    archive_path: str,
    size_bytes: int,
) -> SpecialArchivalRecord:
    """BA-UC-010: Super Admin executes special offline-initiated archival."""
    check_special_archival_auth(ActorRole.SUPER_ADMIN)

    checksum = hashlib.sha256(archive_path.encode()).hexdigest()
    record = SpecialArchivalRecord.objects.create(
        dataset_name=dataset_name,
        source_authority=source_authority,
        reason=reason,
        classification="sensitive",
        archive_path=archive_path,
        performed_by_id=super_admin_id,
        size_bytes=size_bytes,
        checksum=checksum,
    )

    record_audit_event(
        actor_id=super_admin_id,
        actor_username=super_admin_username,
        actor_role="super_admin",
        event_source="admin",
        action="special_archival_executed",
        resource_type="SpecialArchivalRecord",
        resource_id=str(record.id),
        outcome="success",
        details={"dataset_name": dataset_name, "source_authority": source_authority},
    )

    return record
