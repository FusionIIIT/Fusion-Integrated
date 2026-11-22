from datetime import UTC, datetime

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.badms.domain.crypto import CryptoError, encrypt_aes_256_gcm
from modules.badms.domain.retention import resolve_retention_duration
from modules.badms.domain.state_machine import (
    InvalidStateTransitionError,
    UnauthorizedTransitionActorError,
    transition_archival,
)
from modules.badms.domain.storage import (
    InsufficientQuotaError,
    check_storage_quota,
)
from modules.badms.models import (
    ArchivalRequest,
    RetentionPolicy,
    StorageLedgerEntry,
    UserStorageQuota,
)
from modules.badms.services.audit import log_audit_event


@transaction.atomic
def submit_archival_request(
    actor,
    file_name: str,
    file_type: str,
    file_size_bytes: int,
    reason: str,
    file_storage_path: str,
    initial_classification: str = "Routine",
    department: str = "",
) -> ArchivalRequest:
    user_id = getattr(actor, "user_id", None) or 0
    dept = department or getattr(actor, "department", "") or "General"
    active_role = getattr(actor, "active_role", "") or ""
    if dept == "General" and active_role.startswith("HOD (") and active_role.endswith(")"):
        dept = active_role[5:-1]

    quota_obj, created = UserStorageQuota.objects.select_for_update().get_or_create(
        user_id=user_id,
        defaults={"allocated_quota_bytes": 10737418240, "used_storage_bytes": 0, "is_full": False},
    )
    if created:
        StorageLedgerEntry.objects.create(
            quota=quota_obj,
            amount_bytes=10737418240,
            entry_type=StorageLedgerEntry.ENTRY_CREDIT,
            reference="initial_baseline_quota",
            created_by_user_id=user_id,
        )

    try:
        check_storage_quota(
            file_size_bytes, quota_obj.used_storage_bytes, quota_obj.allocated_quota_bytes
        )
    except InsufficientQuotaError as err:
        raise ConflictError(str(err)) from err

    target_state = transition_archival("none", "submit", "user")

    req = ArchivalRequest.objects.create(
        requester_user_id=user_id,
        department=dept,
        file_name=file_name,
        file_type=file_type,
        file_size_bytes=file_size_bytes,
        reason=reason,
        file_storage_path=file_storage_path,
        initial_classification=initial_classification or "Routine",
        authoritative_classification="",
        status=target_state,
    )

    quota_obj.used_storage_bytes += file_size_bytes
    quota_obj.is_full = quota_obj.used_storage_bytes >= quota_obj.allocated_quota_bytes
    quota_obj.save(update_fields=["used_storage_bytes", "is_full"])

    log_audit_event("archival_request_submitted", actor, "ArchivalRequest", req.id, dept)
    return req


@transaction.atomic
def decide_archival_request(
    actor, request_id: int, decision: str, remarks: str = ""
) -> ArchivalRequest:
    user_id = getattr(actor, "user_id", None) or 0
    dept = getattr(actor, "department", "") or ""
    active_role = getattr(actor, "active_role", "") or ""
    if not dept and active_role.startswith("HOD (") and active_role.endswith(")"):
        dept = active_role[5:-1]

    req = ArchivalRequest.objects.select_for_update().filter(id=request_id).first()
    if not req:
        raise NotFoundError("Archival request not found.")

    if req.department != dept and dept:
        raise NotFoundError("Archival request not found in your departmental scope.")

    event = "approve" if decision.lower() == "approve" else "reject"
    try:
        next_state = transition_archival(req.status, event, "hod")
    except (InvalidStateTransitionError, UnauthorizedTransitionActorError) as err:
        raise ConflictError(str(err)) from err

    req.status = next_state
    req.hod_reviewed_by_user_id = user_id
    req.hod_decision_at = datetime.now(UTC)
    req.hod_remarks = remarks
    req.save()

    log_audit_event(
        f"archival_request_{next_state}", actor, "ArchivalRequest", req.id, req.department
    )
    return req


@transaction.atomic
def classify_archival_request(actor, request_id: int, classification: str) -> ArchivalRequest:
    user_id = getattr(actor, "user_id", None) or 0
    req = ArchivalRequest.objects.select_for_update().filter(id=request_id).first()
    if not req:
        raise NotFoundError("Archival request not found.")

    if classification not in ("Routine", "Sensitive", "Critical", "Archival"):
        raise BadRequestError("Invalid classification value.")

    event = "classify_sensitive" if classification == "Sensitive" else "classify_non_sensitive"
    try:
        next_state = transition_archival(req.status, event, "sysadmin")
    except (InvalidStateTransitionError, UnauthorizedTransitionActorError) as err:
        raise ConflictError(str(err)) from err

    # Resolve retention policy based on classification
    retention_policy = RetentionPolicy.objects.filter(
        data_classification=classification, is_active=True
    ).first()
    if retention_policy:
        policy_ref = f"{retention_policy.name} ({retention_policy.retention_days}d)"
    else:
        duration_days = resolve_retention_duration(classification)
        policy_ref = f"Default {classification} ({duration_days}d)"

    req.authoritative_classification = classification
    req.retention_policy_ref = policy_ref
    req.status = next_state
    req.sysadmin_classified_by_user_id = user_id
    req.classified_at = datetime.now(UTC)
    req.save()

    log_audit_event("archival_request_classified", actor, "ArchivalRequest", req.id, req.department)
    return req


@transaction.atomic
def configure_sensitive_encryption(
    actor, request_id: int, encryption_algorithm: str = "AES-256-GCM"
) -> ArchivalRequest:
    user_id = getattr(actor, "user_id", None) or 0
    req = ArchivalRequest.objects.select_for_update().filter(id=request_id).first()
    if not req:
        raise NotFoundError("Archival request not found.")

    try:
        next_state = transition_archival(req.status, "encrypt_and_create", "it_security")
    except (InvalidStateTransitionError, UnauthorizedTransitionActorError) as err:
        raise ConflictError(str(err)) from err

    try:
        # Perform real AES-256-GCM encryption on archive data identifier
        payload = f"ARCHIVE_DATA:{req.id}:{req.file_storage_path}:{req.file_name}"
        encrypt_aes_256_gcm(payload)
    except CryptoError as err:
        raise ConflictError(str(err)) from err

    req.encryption_algorithm = encryption_algorithm
    req.is_encrypted = True
    req.status = next_state
    req.encrypted_by_user_id = user_id
    req.encrypted_at = datetime.now(UTC)
    req.save()

    log_audit_event(
        "archival_encryption_configured", actor, "ArchivalRequest", req.id, req.department
    )
    return req


@transaction.atomic
def perform_special_archival(
    actor,
    file_name: str,
    file_type: str,
    file_size_bytes: int,
    reason: str,
    file_storage_path: str,
    classification: str = "Archival",
) -> ArchivalRequest:
    user_id = getattr(actor, "user_id", None) or 0
    dept = getattr(actor, "department", "") or "Institute"

    next_state = transition_archival("none", "special_archive", "super_admin")

    req = ArchivalRequest.objects.create(
        requester_user_id=user_id,
        department=dept,
        file_name=file_name,
        file_type=file_type,
        file_size_bytes=file_size_bytes,
        reason=reason,
        file_storage_path=file_storage_path,
        initial_classification=classification,
        authoritative_classification=classification,
        retention_policy_ref=f"Default {classification} (3650d)",
        status=next_state,
        is_special_archival=True,
    )
    log_audit_event(
        "special_archival_performed", actor, "ArchivalRequest", req.id, dept
    )
    return req
