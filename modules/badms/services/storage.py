"""The configured Django storage backend is the archive boundary.

Production must bind it to private durable recovery storage with TLS and AES-256
server-side encryption. Local development storage is not suitable for Sensitive data.
"""
from django.conf import settings
from django.core.files.storage import InvalidStorageError, storages

from core.api.exceptions import ConflictError


def badms_storage():
    """Return BADMS recovery storage without changing other modules' storage."""
    return storages["badms"]


def require_secure_storage() -> None:
    if settings.DEBUG and getattr(settings, "BADMS_STORAGE_BACKEND", "local") != "s3":
        return
    if getattr(settings, "BADMS_STORAGE_BACKEND", "local") != "s3":
        raise ConflictError("BADMS recovery storage must use the configured S3 backend.",
                            code="storage_backend_not_configured")
    if not getattr(settings, "BADMS_STORAGE_PRIVATE", False):
        raise ConflictError("Private BADMS recovery storage is not configured.",
                            code="storage_not_configured")
    if not getattr(settings, "BADMS_STORAGE_AES256", False):
        raise ConflictError("AES-256 storage encryption is not configured.",
                            code="storage_encryption_not_configured")
    if not getattr(settings, "BADMS_STORAGE_TLS", False):
        raise ConflictError("TLS for BADMS storage is not configured.",
                            code="storage_tls_not_configured")
    try:
        badms_storage()
    except InvalidStorageError as exc:
        raise ConflictError("BADMS recovery storage is unavailable.",
                            code="storage_unavailable") from exc
    if getattr(settings, "BADMS_STORAGE_BACKEND", "local") == "s3":
        from modules.badms.services.s3_storage import AES256S3Storage

        storage = badms_storage()
        if (not isinstance(storage, AES256S3Storage) or not storage.use_ssl
                or storage.verify is False
                or storage.object_parameters.get("ServerSideEncryption") != "aws:kms"
                or not storage.object_parameters.get("SSEKMSKeyId")):
            raise ConflictError("BADMS S3 transport and encryption are not configured.",
                                code="storage_security_misconfigured")


def retention_deadline(classification):
    from datetime import timedelta

    from django.utils import timezone

    from modules.badms.models import SecurityPolicy

    configured_policy = SecurityPolicy.objects.filter(pk=1).values_list(
        "retention_days", flat=True).first()
    policy = (configured_policy if configured_policy is not None else
              getattr(settings, "BADMS_RETENTION_DAYS", {}))
    days = policy.get(classification) if isinstance(policy, dict) else None
    if type(days) is not int or days < 1:
        raise ConflictError("Institute retention policy is not configured for this classification.",
                            code="retention_policy_missing")
    return timezone.now() + timedelta(days=days)
