"""Business logic services implementing BADMS business rules and workflows."""
from __future__ import annotations

from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.badms.models import (
    BackupOperation,
    BackupSchedule,
    SecureArchivalRequest,
    DataRestorationRequest,
    StorageQuota,
    StorageExtensionRequest,
    BadmsAuditLog,
)
from modules.badms.domain import state_machine as sm


# --- Backup Services (CFR-BA-001, 002, 003, 014, BR-BA-001, 011, 012, 014, 015) ---

@transaction.atomic
def trigger_manual_backup(*, actor, dataset_code: str = "all") -> BackupOperation:
    """BR-BA-001: Only SysAdmin or Super Admin can trigger manual backup."""
    if not (actor.has_permission("badms.backup.trigger")):
        raise PermissionDeniedError("Only SysAdmin or Super Admin can trigger manual backup.")

    op = BackupOperation.objects.create(
        trigger_type="manual",
        dataset_code=dataset_code,
        status="success",
        initiated_by_user_id=actor.user_id,
        dump_location=f"/backups/dumps/{dataset_code}_{timezone.now().strftime('%Y%m%d%H%M%S')}.sql",
        file_size_bytes=1048576,
        integrity_verified=True,
        started_at=timezone.now(),
        completed_at=timezone.now(),
    )
    BadmsAuditLog.objects.create(
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action="manual_backup_triggered",
        entity_type="backup_operation",
        entity_id=op.pk,
        details={"dataset_code": dataset_code, "status": "success"},
    )
    return op


@transaction.atomic
def configure_schedule(*, actor, scope: str, dataset_code: str, cron_expression: str, retention_days: int) -> BackupSchedule:
    """BR-BA-012, BR-BA-019: Global managed by Super Admin; local by SysAdmin."""
    if scope == "global":
        if not actor.has_permission("badms.schedule.manage_global"):
            raise PermissionDeniedError("Only Super Admin can configure global backup schedules.")
    else:
        if not actor.has_permission("badms.schedule.manage_local"):
            raise PermissionDeniedError("SysAdmin permission required to configure local schedule.")

    schedule, _ = BackupSchedule.objects.update_or_create(
        scope=scope,
        dataset_code=dataset_code if scope == "local" else "",
        defaults={
            "cron_expression": cron_expression,
            "retention_days": retention_days,
            "configured_by_user_id": actor.user_id,
            "is_active": True,
        },
    )
    BadmsAuditLog.objects.create(
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action=f"{scope}_schedule_configured",
        entity_type="backup_schedule",
        entity_id=schedule.pk,
        details={"cron": cron_expression, "retention_days": retention_days},
    )
    return schedule


# --- Archival Services (CFR-BA-005..008, 010; Workflows BW-BA-01..03, CW-BA-01) ---

@transaction.atomic
def submit_archival_request(
    *, actor, department: str, file_name: str, file_type: str, file_size_bytes: int, reason: str, initial_classification: str = "routine"
) -> SecureArchivalRequest:
    """User initiates secure archival request (BR-BA-006)."""
    if not (initial_classification in sm.ALL_TIERS):
        initial_classification = sm.TIER_ROUTINE

    req = SecureArchivalRequest.objects.create(
        user_id=actor.user_id,
        department=department,
        file_name=file_name,
        file_type=file_type,
        file_size_bytes=file_size_bytes,
        reason=reason,
        initial_classification=initial_classification,
        status=sm.ARCHIVAL_SUBMITTED,
    )
    BadmsAuditLog.objects.create(
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action="archival_request_submitted",
        entity_type="archival_request",
        entity_id=req.pk,
        details={"initial_classification": initial_classification},
    )
    return req


@transaction.atomic
def hod_review_archival(*, actor, request_id: int, action: str, remarks: str = "") -> SecureArchivalRequest:
    """BR-BA-002, BR-BA-010: HoD approves or rejects departmental archival request."""
    if not actor.has_permission("badms.department.review"):
        raise PermissionDeniedError("HoD review permission required.")

    req = SecureArchivalRequest.objects.select_for_update().get(pk=request_id)
    if req.status != sm.ARCHIVAL_SUBMITTED:
        raise ConflictError(f"Request cannot be reviewed in status {req.status}.")

    new_status = sm.validate_hod_decision(action)
    req.status = new_status
    req.hod_reviewed_by_user_id = actor.user_id
    req.hod_remarks = remarks
    req.hod_reviewed_at = timezone.now()
    req.save()

    BadmsAuditLog.objects.create(
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action=f"archival_hod_{action}",
        entity_type="archival_request",
        entity_id=req.pk,
        details={"remarks": remarks},
    )
    return req


@transaction.atomic
def sysadmin_classify_archival(*, actor, request_id: int, authoritative_classification: str) -> SecureArchivalRequest:
    """BR-BA-004, BR-BA-007, BR-BA-008: SysAdmin sets authoritative classification."""
    if not actor.has_permission("badms.archival.classify_authoritative"):
        raise PermissionDeniedError("SysAdmin classification authority required.")
    if authoritative_classification not in sm.ALL_TIERS:
        raise BadRequestError(f"Invalid tier {authoritative_classification}.")

    req = SecureArchivalRequest.objects.select_for_update().get(pk=request_id)
    if req.status != sm.ARCHIVAL_HOD_APPROVED:
        raise ConflictError(f"Request must be HoD approved prior to classification.")

    req.authoritative_classification = authoritative_classification
    req.classified_by_user_id = actor.user_id
    req.classified_at = timezone.now()
    years = sm.RETENTION_YEARS.get(authoritative_classification, 1)
    req.retention_until = timezone.now() + timedelta(days=365 * years)

    if authoritative_classification == sm.TIER_SENSITIVE:
        req.status = sm.ARCHIVAL_CLASSIFIED  # Routes to IT Security for encryption
    else:
        # Non-sensitive / routine / archival completes directly (BW-BA-02)
        req.status = sm.ARCHIVAL_COMPLETED
        req.archive_location = f"/archives/{req.department}/{req.pk}_{req.file_name}"

    req.save()
    BadmsAuditLog.objects.create(
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action="archival_classified",
        entity_type="archival_request",
        entity_id=req.pk,
        details={"classification": authoritative_classification},
    )
    return req


@transaction.atomic
def it_security_configure_encryption(*, actor, request_id: int, algorithm: str = "AES-256") -> SecureArchivalRequest:
    """BR-BA-003, BR-BA-007: IT Security configures encryption for Sensitive data (BW-BA-03)."""
    if not actor.has_permission("badms.security.manage"):
        raise PermissionDeniedError("IT Security authority required.")

    req = SecureArchivalRequest.objects.select_for_update().get(pk=request_id)
    if req.status != sm.ARCHIVAL_CLASSIFIED or req.authoritative_classification != sm.TIER_SENSITIVE:
        raise ConflictError("Request is not ready for encryption configuration.")

    req.is_encrypted = True
    req.encryption_algorithm = algorithm
    req.encryption_configured_by = actor.user_id
    req.status = sm.ARCHIVAL_COMPLETED
    req.archive_location = f"/archives/encrypted/{req.pk}_{req.file_name}.enc"
    req.save()

    BadmsAuditLog.objects.create(
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action="encryption_configured",
        entity_type="archival_request",
        entity_id=req.pk,
        details={"algorithm": algorithm},
    )
    return req


# --- Storage Extension Services (CFR-BA-012, 013, 017; Workflows BW-BA-04..05, CW-BA-02) ---

@transaction.atomic
def submit_storage_extension(*, actor, department: str, requested_additional_mb: int, reason: str) -> StorageExtensionRequest:
    """User requests additional storage when quota is full (BR-BA-016)."""
    quota, _ = StorageQuota.objects.get_or_create(user_id=actor.user_id)
    sm.validate_storage_quota_threshold(quota.used_mb, quota.allocated_mb)

    req = StorageExtensionRequest.objects.create(
        user_id=actor.user_id,
        department=department,
        requested_additional_mb=requested_additional_mb,
        reason=reason,
        status=sm.STORAGE_SUBMITTED,
    )
    BadmsAuditLog.objects.create(
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action="storage_extension_submitted",
        entity_type="storage_extension_request",
        entity_id=req.pk,
        details={"requested_mb": requested_additional_mb},
    )
    return req


@transaction.atomic
def hod_review_storage_extension(*, actor, request_id: int, action: str, remarks: str = "") -> StorageExtensionRequest:
    """HoD decides storage extension (BR-BA-009, BR-BA-017, BW-BA-04/05)."""
    if not actor.has_permission("badms.department.review"):
        raise PermissionDeniedError("HoD review permission required.")

    req = StorageExtensionRequest.objects.select_for_update().get(pk=request_id)
    if req.status != sm.STORAGE_SUBMITTED:
        raise ConflictError(f"Cannot review request in status {req.status}.")

    if action == "approve":
        req.status = sm.STORAGE_APPROVED
        quota, _ = StorageQuota.objects.get_or_create(user_id=req.user_id)
        quota.allocated_mb += req.requested_additional_mb
        quota.save()
    else:
        req.status = sm.STORAGE_REJECTED

    req.hod_reviewed_by_user_id = actor.user_id
    req.hod_remarks = remarks
    req.save()

    BadmsAuditLog.objects.create(
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action=f"storage_extension_hod_{action}",
        entity_type="storage_extension_request",
        entity_id=req.pk,
        details={"remarks": remarks},
    )
    return req


# --- Data Restoration Services (CFR-BA-011; Workflows BW-BA-06..07, CW-BA-03) ---

@transaction.atomic
def submit_restoration_request(*, actor, archival_request_id: int, reason: str) -> DataRestorationRequest:
    """User initiates restoration request (BW-BA-06, BW-BA-07)."""
    archival = SecureArchivalRequest.objects.get(pk=archival_request_id)

    # If authoritative classification is Sensitive, requires SysAdmin approval (BR-BA-005, BW-BA-07)
    initial_status = sm.RESTORATION_SUBMITTED
    if archival.authoritative_classification != sm.TIER_SENSITIVE:
        # Standard restoration non-sensitive path auto completes (BW-BA-06)
        initial_status = sm.RESTORATION_COMPLETED

    rest_req = DataRestorationRequest.objects.create(
        user_id=actor.user_id,
        archival_request=archival,
        reason=reason,
        status=initial_status,
        restored_at=timezone.now() if initial_status == sm.RESTORATION_COMPLETED else None,
    )
    BadmsAuditLog.objects.create(
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action="restoration_requested",
        entity_type="restoration_request",
        entity_id=rest_req.pk,
        details={"is_sensitive": (archival.authoritative_classification == sm.TIER_SENSITIVE)},
    )
    return rest_req


@transaction.atomic
def sysadmin_review_restoration(*, actor, restoration_id: int, action: str, remarks: str = "") -> DataRestorationRequest:
    """SysAdmin reviews sensitive data restoration (BR-BA-005, BW-BA-07)."""
    if not actor.has_permission("badms.restoration.approve_sensitive"):
        raise PermissionDeniedError("SysAdmin restoration approval permission required.")

    req = DataRestorationRequest.objects.select_for_update().get(pk=restoration_id)
    if req.status != sm.RESTORATION_SUBMITTED:
        raise ConflictError(f"Request cannot be reviewed in status {req.status}.")

    if action == "approve":
        req.status = sm.RESTORATION_COMPLETED
        req.restored_at = timezone.now()
    else:
        req.status = sm.RESTORATION_SYSADMIN_REJECTED

    req.sysadmin_reviewed_by_user_id = actor.user_id
    req.sysadmin_remarks = remarks
    req.save()

    BadmsAuditLog.objects.create(
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action=f"restoration_sysadmin_{action}",
        entity_type="restoration_request",
        entity_id=req.pk,
        details={"remarks": remarks},
    )
    return req
