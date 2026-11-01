"""Secure Archival domain service for BADMS."""
from __future__ import annotations

import hashlib
from datetime import date
from typing import Any

from django.db import transaction
from django.utils import timezone
from core.files.validators import sanitise_filename
from modules.badms.models import (
    ArchivalRequest,
    ArchiveClassification,
    ArchiveStatus,
)
from modules.badms.services.audit import record_audit
from modules.badms.services.department import get_user_department
from modules.badms.services.notifications import send_notification
from modules.badms.services.storage import (
    QuotaExceededError,
    check_quota,
    consume_quota,
    release_quota,
)


class ArchivalValidationError(Exception):
    """Raised when submitted archive request fails validation."""
    pass


def validate_archival_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Validate user archival submission data."""
    file_name = (data.get("file_name") or "").strip()
    if not file_name:
        raise ArchivalValidationError("File name is required.")
    sanitized_name = sanitise_filename(file_name)

    file_type = (data.get("file_type") or "").strip().lower().lstrip(".")
    if not file_type:
        raise ArchivalValidationError("File type is required.")

    reason = (data.get("reason") or "").strip()
    if not reason:
        raise ArchivalValidationError("Reason for archival is required.")

    doc_date = data.get("document_date")
    if not doc_date:
        raise ArchivalValidationError("Document date is required.")
    if isinstance(doc_date, str):
        try:
            doc_date = date.fromisoformat(doc_date)
        except ValueError:
            raise ArchivalValidationError("Invalid document date format. Use YYYY-MM-DD.")

    owners = data.get("owners")
    if owners is None or (isinstance(owners, list) and len(owners) == 0):
        owners = []
    elif isinstance(owners, str):
        owners = [o.strip() for o in owners.split(",") if o.strip()]

    file_size_bytes = data.get("file_size_bytes", 0)
    try:
        file_size_bytes = int(file_size_bytes)
        if file_size_bytes < 0:
            raise ValueError()
    except (TypeError, ValueError):
        raise ArchivalValidationError("File size must be a non-negative integer.")

    initial_classification = (
        data.get("initial_classification") or ArchiveClassification.ROUTINE
    ).lower()
    if initial_classification not in ArchiveClassification.values:
        initial_classification = ArchiveClassification.ROUTINE

    return {
        "file_name": sanitized_name,
        "file_type": file_type,
        "reason": reason,
        "document_date": doc_date,
        "owners": owners,
        "file_size_bytes": file_size_bytes,
        "initial_classification": initial_classification,
        "attachment_path": data.get("attachment_path", ""),
        "checksum": data.get("checksum", ""),
    }


@transaction.atomic
def submit_archival_request(
    *,
    user_id: int,
    user_role: str = "",
    payload: dict[str, Any],
    file_bytes: bytes | None = None,
) -> ArchivalRequest:
    """Validate, enforce quota, create, and route an archival request."""
    validated = validate_archival_payload(payload)

    # Compute checksum if bytes provided
    if file_bytes:
        validated["file_size_bytes"] = len(file_bytes)
        validated["checksum"] = hashlib.sha256(file_bytes).hexdigest()

    file_size = validated["file_size_bytes"]

    # Quota verification & consumption
    is_sufficient, remaining, allocated = check_quota(user_id, file_size)
    if not is_sufficient:
        raise QuotaExceededError(requested=file_size, available=remaining, allocated=allocated)

    consume_quota(user_id, file_size)

    # Department resolution
    department = get_user_department(user_id) or payload.get("department", "GENERAL")

    # Ensure requester is included in owners if empty
    owners = validated["owners"]
    if not owners:
        owners = [f"u{user_id}"]

    # Create archival request record
    archive_request = ArchivalRequest.objects.create(
        user_id=user_id,
        department=department,
        file_name=validated["file_name"],
        document_date=validated["document_date"],
        owners=owners,
        file_type=validated["file_type"],
        file_size_bytes=file_size,
        attachment_path=validated["attachment_path"],
        reason=validated["reason"],
        initial_classification=validated["initial_classification"],
        status=ArchiveStatus.SUBMITTED,
        checksum=validated["checksum"],
    )

    # Create audit log
    record_audit(
        actor_user_id=user_id,
        actor_role=user_role,
        action="badms.archive.submit",
        target_type="archive_request",
        target_id=archive_request.pk,
        outcome="success",
        details={
            "file_name": archive_request.file_name,
            "department": department,
            "file_size_bytes": file_size,
            "initial_classification": archive_request.initial_classification,
        },
    )

    # Send confirmation notification to requester
    send_notification(
        user_id=user_id,
        subject=f"Archival Request Submitted: {archive_request.file_name}",
        message=(
            f"Your archival request #{archive_request.pk} for '{archive_request.file_name}' "
            f"has been submitted and routed to the {department} Head of Department for review."
        ),
        notification_type="archive_submitted",
        related_object_id=archive_request.pk,
    )

    # Send routing notification to HoD role
    send_notification(
        user_id=0,  # Broadcast or pooled for role
        recipient_role="HOD",
        subject=f"New Archival Review: {archive_request.file_name} ({department})",
        message=(
            f"A new archival request #{archive_request.pk} for '{archive_request.file_name}' "
            f"has been submitted by User {user_id} and requires your HoD approval."
        ),
        notification_type="hod_review_required",
        related_object_id=archive_request.pk,
    )

    return archive_request


@transaction.atomic
def hod_review_request(
    *,
    archive_id: int,
    reviewer_id: int,
    reviewer_role: str,
    decision: str,
    comments: str = "",
) -> ArchivalRequest:
    """Process HoD review decision (approve or reject) for an archival request."""
    archive = ArchivalRequest.objects.select_for_update().filter(pk=archive_id).first()
    if not archive:
        raise ArchivalValidationError(f"Archival request #{archive_id} does not exist.")

    if archive.status != ArchiveStatus.SUBMITTED:
        raise ArchivalValidationError(
            f"Cannot review request #{archive_id}: current status is '{archive.status}', expected '{ArchiveStatus.SUBMITTED}'."
        )

    decision_clean = (decision or "").strip().lower()
    if decision_clean not in ("approve", "reject"):
        raise ArchivalValidationError("Decision must be either 'approve' or 'reject'.")

    now = timezone.now()
    archive.hod_user_id = reviewer_id
    archive.hod_comments = comments
    archive.hod_decided_at = now

    if decision_clean == "reject":
        if not comments.strip():
            raise ArchivalValidationError("Comments are required when rejecting an archival request.")
        archive.status = ArchiveStatus.REJECTED
        archive.save(update_fields=["status", "hod_user_id", "hod_comments", "hod_decided_at", "updated_at"])

        # Release consumed quota
        release_quota(archive.user_id, archive.file_size_bytes)

        # Audit log
        record_audit(
            actor_user_id=reviewer_id,
            actor_role=reviewer_role,
            action="badms.archive.hod_reject",
            target_type="archive_request",
            target_id=archive.pk,
            outcome="rejected",
            details={"comments": comments, "department": archive.department},
        )

        # Notify requester
        send_notification(
            user_id=archive.user_id,
            subject=f"Archival Request Rejected: {archive.file_name}",
            message=f"Your archival request #{archive.pk} for '{archive.file_name}' was rejected by the Head of Department. Reason: {comments}",
            notification_type="archive_rejected",
            related_object_id=archive.pk,
        )
    else:
        archive.status = ArchiveStatus.HOD_APPROVED
        archive.save(update_fields=["status", "hod_user_id", "hod_comments", "hod_decided_at", "updated_at"])

        # Audit log
        record_audit(
            actor_user_id=reviewer_id,
            actor_role=reviewer_role,
            action="badms.archive.hod_approve",
            target_type="archive_request",
            target_id=archive.pk,
            outcome="success",
            details={"comments": comments, "department": archive.department},
        )

        # Notify requester
        send_notification(
            user_id=archive.user_id,
            subject=f"Archival Request Approved by HoD: {archive.file_name}",
            message=f"Your archival request #{archive.pk} for '{archive.file_name}' was approved by your Head of Department and forwarded to System Administration for classification.",
            notification_type="archive_hod_approved",
            related_object_id=archive.pk,
        )

        # Notify SysAdmin role
        send_notification(
            user_id=0,
            recipient_role="sysadmin",
            subject=f"Pending Classification: Archive #{archive.pk} ({archive.department})",
            message=f"Archive #{archive.pk} ('{archive.file_name}') has been HoD-approved and is awaiting authoritative classification.",
            notification_type="classification_required",
            related_object_id=archive.pk,
        )

    return archive


@transaction.atomic
def classify_archival_request(
    *,
    archive_id: int,
    sysadmin_id: int,
    sysadmin_role: str,
    classification: str,
    comments: str = "",
) -> ArchivalRequest:
    """Assign authoritative classification to a HoD-approved archival request."""
    archive = ArchivalRequest.objects.select_for_update().filter(pk=archive_id).first()
    if not archive:
        raise ArchivalValidationError(f"Archival request #{archive_id} does not exist.")

    if archive.status != ArchiveStatus.HOD_APPROVED:
        raise ArchivalValidationError(
            f"Cannot classify request #{archive_id}: request must be 'hod_approved' (current status: '{archive.status}')."
        )

    class_clean = (classification or "").strip().lower()
    if class_clean not in ArchiveClassification.values:
        raise ArchivalValidationError(
            f"Invalid classification '{classification}'. Allowed: {list(ArchiveClassification.values)}."
        )

    now = timezone.now()
    archive.authoritative_classification = class_clean
    archive.sysadmin_user_id = sysadmin_id
    archive.sysadmin_comments = comments
    archive.sysadmin_classified_at = now

    if class_clean == ArchiveClassification.SENSITIVE:
        # Sensitive requests routed to IT Security for encryption configuration
        archive.status = ArchiveStatus.ROUTED_TO_SECURITY
        archive.save(
            update_fields=[
                "authoritative_classification",
                "status",
                "sysadmin_user_id",
                "sysadmin_comments",
                "sysadmin_classified_at",
                "updated_at",
            ]
        )

        # Audit log
        record_audit(
            actor_user_id=sysadmin_id,
            actor_role=sysadmin_role,
            action="badms.archive.classify",
            target_type="archive_request",
            target_id=archive.pk,
            outcome="success",
            details={
                "classification": class_clean,
                "comments": comments,
                "routed_to": "IT Security",
            },
        )

        # Notify IT Security role
        send_notification(
            user_id=0,
            recipient_role="it_security",
            subject=f"Sensitive Archive #{archive.pk} Requires Encryption Configuration",
            message=(
                f"Archive #{archive.pk} ('{archive.file_name}') classified as Sensitive by SysAdmin "
                f"and routed to IT Security for AES-256 encryption configuration."
            ),
            notification_type="security_encryption_required",
            related_object_id=archive.pk,
        )

        # Notify requester
        send_notification(
            user_id=archive.user_id,
            subject=f"Archive #{archive.pk} Classified as Sensitive",
            message=f"Your archive request #{archive.pk} was classified as Sensitive and routed to IT Security for encryption.",
            notification_type="archive_classified",
            related_object_id=archive.pk,
        )
    else:
        # Non-Sensitive (Routine, Archival, Critical) -> policy applied
        archive.status = ArchiveStatus.POLICY_APPLIED
        archive.save(
            update_fields=[
                "authoritative_classification",
                "status",
                "sysadmin_user_id",
                "sysadmin_comments",
                "sysadmin_classified_at",
                "updated_at",
            ]
        )

        # Audit log
        record_audit(
            actor_user_id=sysadmin_id,
            actor_role=sysadmin_role,
            action="badms.archive.classify",
            target_type="archive_request",
            target_id=archive.pk,
            outcome="success",
            details={
                "classification": class_clean,
                "comments": comments,
                "policy_applied": True,
            },
        )

        # Notify requester
        send_notification(
            user_id=archive.user_id,
            subject=f"Archive #{archive.pk} Classified ({class_clean.title()})",
            message=f"Your archive request #{archive.pk} was classified as {class_clean.title()} and policy applied.",
            notification_type="archive_classified",
            related_object_id=archive.pk,
        )

    return archive
