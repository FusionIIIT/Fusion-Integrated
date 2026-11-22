"""Read-only selectors for user storage quotas and storage extension requests."""

from __future__ import annotations

from django.db.models import QuerySet

from modules.badms.models import StorageExtensionRequest, UserStorageQuota


def get_user_storage_quota(user_id: int) -> UserStorageQuota | None:
    return UserStorageQuota.objects.filter(user_id=user_id).first()


def list_storage_extensions(
    *,
    user_id: int | None = None,
    department_id: int | None = None,
    status: str | None = None,
) -> QuerySet[StorageExtensionRequest]:
    qs = StorageExtensionRequest.objects.all().order_by("-created_at")
    if user_id is not None:
        qs = qs.filter(user_id=user_id)
    if department_id is not None:
        qs = qs.filter(department_id=department_id)
    if status:
        qs = qs.filter(status=status)
    return qs


def get_storage_extension_by_id(extension_id: int) -> StorageExtensionRequest | None:
    return StorageExtensionRequest.objects.filter(id=extension_id).first()


def list_hod_storage_extension_queue(department_id: int) -> QuerySet[StorageExtensionRequest]:
    return StorageExtensionRequest.objects.filter(
        department_id=department_id,
        status="submitted",
    ).order_by("-created_at")
