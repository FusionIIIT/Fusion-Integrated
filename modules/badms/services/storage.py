"""Storage quota management service for BADMS."""
from __future__ import annotations

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from modules.badms.models import (
    StorageExtensionRequest,
    StorageExtensionStatus,
    UserStorageQuota,
)
from modules.badms.services.audit import record_audit
from modules.badms.services.department import can_review_department_request, get_user_department
from modules.badms.services.notifications import send_notification


class StorageExtensionError(Exception):
    """Raised when storage extension validation or workflow fails."""
    pass


class QuotaExceededError(Exception):
    """Raised when an operation would exceed the user's allocated storage quota."""

    def __init__(self, requested: int, available: int, allocated: int):
        self.requested = requested
        self.available = available
        self.allocated = allocated
        super().__init__(
            f"Storage quota exceeded: requested {requested} bytes, but only {available} bytes remaining (allocated {allocated} bytes)."
        )


def get_or_create_user_quota(user_id: int, department: str = "") -> UserStorageQuota:
    """Retrieve or initialize the storage quota record for a user."""
    if not department:
        department = get_user_department(user_id) or "GENERAL"

    quota, created = UserStorageQuota.objects.get_or_create(
        user_id=user_id,
        defaults={
            "department": department,
            "allocated_bytes": UserStorageQuota.DEFAULT_QUOTA_BYTES,
            "used_bytes": 0,
        },
    )
    if not created and department and not quota.department:
        quota.department = department
        quota.save(update_fields=["department"])
    return quota


def check_quota(user_id: int, incoming_bytes: int) -> tuple[bool, int, int]:
    """Check if the user has sufficient remaining storage quota.

    Returns:
        (is_sufficient, remaining_bytes, allocated_bytes)
    """
    quota = get_or_create_user_quota(user_id)
    remaining = quota.remaining_bytes
    return incoming_bytes <= remaining, remaining, quota.allocated_bytes


@transaction.atomic
def consume_quota(user_id: int, file_size_bytes: int) -> UserStorageQuota:
    """Validate and consume storage quota for an uploaded/archived file."""
    if file_size_bytes <= 0:
        return get_or_create_user_quota(user_id)

    quota = UserStorageQuota.objects.select_for_update().filter(user_id=user_id).first()
    if not quota:
        dept = get_user_department(user_id) or "GENERAL"
        quota = UserStorageQuota.objects.create(
            user_id=user_id,
            department=dept,
            allocated_bytes=UserStorageQuota.DEFAULT_QUOTA_BYTES,
            used_bytes=0,
        )

    if quota.used_bytes + file_size_bytes > quota.allocated_bytes:
        remaining = max(0, quota.allocated_bytes - quota.used_bytes)
        raise QuotaExceededError(
            requested=file_size_bytes,
            available=remaining,
            allocated=quota.allocated_bytes,
        )

    quota.used_bytes = F("used_bytes") + file_size_bytes
    quota.save(update_fields=["used_bytes"])
    quota.refresh_from_db()
    return quota


@transaction.atomic
def release_quota(user_id: int, file_size_bytes: int) -> UserStorageQuota:
    """Release previously consumed storage quota (e.g. upon rejection or deletion)."""
    if file_size_bytes <= 0:
        return get_or_create_user_quota(user_id)

    quota = UserStorageQuota.objects.select_for_update().filter(user_id=user_id).first()
    if not quota:
        return get_or_create_user_quota(user_id)

    new_used = max(0, quota.used_bytes - file_size_bytes)
    quota.used_bytes = new_used
    quota.save(update_fields=["used_bytes"])
    return quota


def submit_storage_extension(
    *,
    user_id: int,
    user_role: str,
    requested_bytes: int,
    reason: str,
) -> StorageExtensionRequest:
    """Submit a storage quota extension request routed to the user's HoD."""
    if requested_bytes <= 0:
        raise StorageExtensionError("Requested storage bytes must be greater than zero.")

    clean_reason = (reason or "").strip()
    if not clean_reason:
        raise StorageExtensionError("A valid justification reason is required for storage extension.")

    dept = get_user_department(user_id) or "GENERAL"
    quota = get_or_create_user_quota(user_id, department=dept)

    ext = StorageExtensionRequest.objects.create(
        user_id=user_id,
        department=dept,
        current_allocated_bytes=quota.allocated_bytes,
        requested_bytes=requested_bytes,
        reason=clean_reason,
        status=StorageExtensionStatus.SUBMITTED,
    )

    record_audit(
        actor_user_id=user_id,
        actor_role=user_role,
        action="badms.storage.submit",
        target_type="storage_extension",
        target_id=ext.pk,
        outcome="success",
        details={
            "requested_bytes": requested_bytes,
            "department": dept,
            "current_allocated_bytes": quota.allocated_bytes,
        },
    )

    send_notification(
        user_id=user_id,
        subject=f"Storage Extension Requested (+{requested_bytes // (1024 * 1024)} MB)",
        message=(
            f"Your storage quota extension request #{ext.pk} for +{requested_bytes} bytes "
            f"has been submitted and routed to the {dept} Head of Department for review."
        ),
        notification_type="storage_extension_submitted",
        related_object_id=ext.pk,
    )

    send_notification(
        user_id=0,
        recipient_role="HOD",
        subject=f"Storage Extension Review: User {user_id} ({dept})",
        message=(
            f"User {user_id} ({dept}) has requested a storage quota extension of +{requested_bytes} bytes. "
            f"Reason: {clean_reason}"
        ),
        notification_type="storage_extension_review_required",
        related_object_id=ext.pk,
    )

    return ext


@transaction.atomic
def process_storage_extension_decision(
    *,
    request_id: int,
    reviewer_id: int,
    reviewer_role: str,
    decision: str,
    comments: str = "",
) -> StorageExtensionRequest:
    """Process HoD review decision (approve or reject) for a storage extension request."""
    ext = StorageExtensionRequest.objects.select_for_update().filter(pk=request_id).first()
    if not ext:
        raise StorageExtensionError(f"Storage extension request #{request_id} does not exist.")

    if ext.status != StorageExtensionStatus.SUBMITTED:
        raise StorageExtensionError(
            f"Cannot process request #{request_id}: current status is '{ext.status}', expected '{StorageExtensionStatus.SUBMITTED}'."
        )

    decision_clean = (decision or "").strip().lower()
    if decision_clean not in ("approve", "reject"):
        raise StorageExtensionError("Decision must be either 'approve' or 'reject'.")

    now = timezone.now()
    ext.hod_user_id = reviewer_id
    ext.hod_comments = (comments or "").strip()
    ext.decided_at = now

    if decision_clean == "reject":
        if not ext.hod_comments:
            raise StorageExtensionError("Comments are required when rejecting a storage extension request.")
        ext.status = StorageExtensionStatus.REJECTED
        ext.save(update_fields=["status", "hod_user_id", "hod_comments", "decided_at", "updated_at"])

        record_audit(
            actor_user_id=reviewer_id,
            actor_role=reviewer_role,
            action="badms.storage.reject",
            target_type="storage_extension",
            target_id=ext.pk,
            outcome="rejected",
            details={
                "reason": ext.hod_comments,
                "department": ext.department,
            },
        )

        send_notification(
            user_id=ext.user_id,
            subject=f"Storage Extension Request #{ext.pk} Rejected",
            message=(
                f"Your storage extension request #{ext.pk} was rejected by the Head of Department. "
                f"Comments: {ext.hod_comments}"
            ),
            notification_type="storage_extension_rejected",
            related_object_id=ext.pk,
        )
    else:
        # Approve: Increase user's allocated storage quota
        quota = UserStorageQuota.objects.select_for_update().filter(user_id=ext.user_id).first()
        if not quota:
            quota = get_or_create_user_quota(ext.user_id, department=ext.department)

        quota.allocated_bytes = F("allocated_bytes") + ext.requested_bytes
        quota.save(update_fields=["allocated_bytes"])
        quota.refresh_from_db()

        ext.status = StorageExtensionStatus.HOD_APPROVED
        ext.save(update_fields=["status", "hod_user_id", "hod_comments", "decided_at", "updated_at"])

        record_audit(
            actor_user_id=reviewer_id,
            actor_role=reviewer_role,
            action="badms.storage.approve",
            target_type="storage_extension",
            target_id=ext.pk,
            outcome="success",
            details={
                "added_bytes": ext.requested_bytes,
                "new_allocated_bytes": quota.allocated_bytes,
                "department": ext.department,
            },
        )

        send_notification(
            user_id=ext.user_id,
            subject=f"Storage Extension Request #{ext.pk} Approved",
            message=(
                f"Your storage quota extension request #{ext.pk} for +{ext.requested_bytes} bytes was approved! "
                f"Your updated quota allocation is now {quota.allocated_bytes} bytes."
            ),
            notification_type="storage_extension_approved",
            related_object_id=ext.pk,
        )

    return ext
