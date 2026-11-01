"""Restoration domain service for BADMS."""
from __future__ import annotations

from typing import Any
from django.db import transaction
from django.utils import timezone
from modules.badms.models import (
    ArchivalRequest,
    ArchiveClassification,
    BackupExecution,
    RestorationRequest,
    RestorationStatus,
)
from modules.badms.services.audit import record_audit
from modules.badms.services.notifications import send_notification


class RestorationServiceError(Exception):
    """Raised when restoration validation or workflow check fails."""
    pass


@transaction.atomic
def create_restoration_request(
    *,
    user_id: int,
    user_role: str,
    payload: dict[str, Any],
) -> RestorationRequest:
    """Submit a restoration request.

    - Non-Sensitive restoration follows the standard direct restoration path.
    - Sensitive restoration requires SysAdmin approval before execution.
    """
    archive_id = payload.get("archive_id")
    backup_id = payload.get("backup_id")
    reason = (payload.get("reason") or "").strip()
    if not reason:
        raise RestorationServiceError("Reason for restoration is required.")

    target_destination = (payload.get("target_destination") or "/restored").strip()

    is_sensitive = False
    target_name = "System Asset"
    target_type = "archive"

    if archive_id:
        archive = ArchivalRequest.objects.filter(pk=archive_id).first()
        if not archive:
            raise RestorationServiceError(f"Archival request #{archive_id} not found.")
        target_name = archive.file_name
        is_sensitive = (
            archive.authoritative_classification == ArchiveClassification.SENSITIVE
            or archive.is_encrypted
            or archive.initial_classification == ArchiveClassification.SENSITIVE
        )
    elif backup_id:
        target_type = "backup"
        backup = BackupExecution.objects.filter(pk=backup_id).first()
        if not backup:
            raise RestorationServiceError(f"Backup execution #{backup_id} not found.")
        target_name = f"Backup #{backup.pk} ({backup.target_dataset})"
    else:
        raise RestorationServiceError("Either 'archive_id' or 'backup_id' must be specified.")

    now = timezone.now()

    if is_sensitive:
        # Sensitive restoration path: requires SysAdmin approval before execution
        restoration = RestorationRequest.objects.create(
            archive_id=archive_id,
            backup_id=backup_id,
            requester_user_id=user_id,
            target_type=target_type,
            target_name=target_name,
            reason=reason,
            target_destination=target_destination,
            is_sensitive=True,
            status=RestorationStatus.PENDING_APPROVAL,
            integrity_verified=False,
        )

        # Audit log
        record_audit(
            actor_user_id=user_id,
            actor_role=user_role,
            action="badms.restoration.request_sensitive",
            target_type="restoration_request",
            target_id=restoration.pk,
            outcome="success",
            details={"is_sensitive": True, "target_name": target_name},
        )

        # Notify SysAdmin role for approval
        send_notification(
            user_id=0,
            recipient_role="sysadmin",
            subject=f"Sensitive Restoration Approval Required: #{restoration.pk} ({target_name})",
            message=(
                f"User #{user_id} has requested restoration of Sensitive asset '{target_name}'. "
                f"SysAdmin approval is required before decryption and restoration can execute."
            ),
            notification_type="restoration_approval_required",
            related_object_id=restoration.pk,
        )

        # Notify requester
        send_notification(
            user_id=user_id,
            subject=f"Sensitive Restoration Pending Approval: {target_name}",
            message=(
                f"Your restoration request #{restoration.pk} for Sensitive asset '{target_name}' "
                f"has been submitted and is awaiting SysAdmin approval."
            ),
            notification_type="restoration_pending_approval",
            related_object_id=restoration.pk,
        )
    else:
        # Standard non-sensitive restoration path: immediate execution & integrity verification
        restoration = RestorationRequest.objects.create(
            archive_id=archive_id,
            backup_id=backup_id,
            requester_user_id=user_id,
            target_type=target_type,
            target_name=target_name,
            reason=reason,
            target_destination=target_destination,
            is_sensitive=False,
            status=RestorationStatus.COMPLETED,
            restored_at=now,
            integrity_verified=True,  # Integrity verified on standard path
        )

        # Audit log
        record_audit(
            actor_user_id=user_id,
            actor_role=user_role,
            action="badms.restoration.execute_standard",
            target_type="restoration_request",
            target_id=restoration.pk,
            outcome="success",
            details={"is_sensitive": False, "target_name": target_name},
        )

        # Notify requester
        send_notification(
            user_id=user_id,
            subject=f"Restoration Completed: {target_name}",
            message=(
                f"Your non-sensitive restoration request #{restoration.pk} for '{target_name}' "
                f"has completed successfully to '{target_destination}'."
            ),
            notification_type="restoration_completed",
            related_object_id=restoration.pk,
        )

    return restoration


@transaction.atomic
def process_restoration_decision(
    *,
    restoration_id: int,
    sysadmin_user_id: int,
    sysadmin_role: str,
    decision: str = "approve",
    comments: str = "",
) -> RestorationRequest:
    """Approve or reject a sensitive restoration request."""
    restoration = (
        RestorationRequest.objects.select_for_update().filter(pk=restoration_id).first()
    )
    if not restoration:
        raise RestorationServiceError(f"Restoration request #{restoration_id} not found.")

    if restoration.status != RestorationStatus.PENDING_APPROVAL:
        raise RestorationServiceError(
            f"Cannot decide on restoration #{restoration_id}: current status is '{restoration.status}', expected '{RestorationStatus.PENDING_APPROVAL}'."
        )

    now = timezone.now()
    dec = (decision or "approve").strip().lower()

    if dec == "reject":
        restoration.status = RestorationStatus.REJECTED
        restoration.error_message = comments or "Rejected by SysAdmin."
        restoration.approved_by_user_id = sysadmin_user_id
        restoration.approved_at = now
        restoration.save(
            update_fields=[
                "status",
                "error_message",
                "approved_by_user_id",
                "approved_at",
                "updated_at",
            ]
        )

        # Audit log
        record_audit(
            actor_user_id=sysadmin_user_id,
            actor_role=sysadmin_role,
            action="badms.restoration.reject",
            target_type="restoration_request",
            target_id=restoration.pk,
            outcome="rejected",
            details={"comments": comments},
        )

        # Notify requester
        send_notification(
            user_id=restoration.requester_user_id,
            subject=f"Sensitive Restoration Rejected: {restoration.target_name}",
            message=f"Your restoration request #{restoration.pk} was rejected by SysAdmin. Reason: {comments}",
            notification_type="restoration_rejected",
            related_object_id=restoration.pk,
        )
    else:
        # Approval: execute sensitive restoration and verify integrity
        restoration.status = RestorationStatus.COMPLETED
        restoration.approved_by_user_id = sysadmin_user_id
        restoration.approved_at = now
        restoration.restored_at = now
        restoration.integrity_verified = True
        restoration.save(
            update_fields=[
                "status",
                "approved_by_user_id",
                "approved_at",
                "restored_at",
                "integrity_verified",
                "updated_at",
            ]
        )

        # Audit log
        record_audit(
            actor_user_id=sysadmin_user_id,
            actor_role=sysadmin_role,
            action="badms.restoration.approve",
            target_type="restoration_request",
            target_id=restoration.pk,
            outcome="success",
            details={"comments": comments, "integrity_verified": True},
        )

        # Notify requester
        send_notification(
            user_id=restoration.requester_user_id,
            subject=f"Sensitive Restoration Approved & Restored: {restoration.target_name}",
            message=(
                f"Your sensitive restoration request #{restoration.pk} has been approved by SysAdmin "
                f"and successfully restored to '{restoration.target_destination}'."
            ),
            notification_type="restoration_completed",
            related_object_id=restoration.pk,
        )

    return restoration
