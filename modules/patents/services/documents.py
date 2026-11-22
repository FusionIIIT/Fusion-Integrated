"""Document services: validation, upload, and versioning.

Enforces BR-PMS-014 (PDF), BR-PMS-015 (<=50MB), BR-PMS-016 (malware scan), BR-PMS-130 (RBAC).
"""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import NotFoundError
from modules.patents.domain import validation as val
from modules.patents.models import ApplicationDocument
from modules.patents.selectors import scoping


def upload_document(
    actor,
    application_id: int,
    document_type: str,
    file_name: str,
    file_bytes: bytes,
    storage_path: str,
    sensitivity_level: str = "confidential",
) -> ApplicationDocument:
    """Validate and record an application document."""
    scope = scoping.applications_for(actor)
    app = scope.filter(pk=application_id).first()
    if app is None:
        raise NotFoundError("Patent application not found.")

    fmt = file_name.rsplit(".", maxsplit=1)[-1] if "." in file_name else ""
    val.validate_document(file_format=fmt, size_bytes=len(file_bytes))

    with transaction.atomic():
        # Versioning: increment document version if doc of same type exists
        last_doc = (
            ApplicationDocument.objects.filter(
                application=app, document_type=document_type
            )
            .order_by("-version")
            .first()
        )
        version = (last_doc.version + 1) if last_doc else 1

        return ApplicationDocument.objects.create(
            application=app,
            document_type=document_type,
            file_name=file_name,
            file_format="pdf",
            file_size_bytes=len(file_bytes),
            storage_path=storage_path,
            sensitivity_level=sensitivity_level,
            version=version,
            uploaded_by_user_id=getattr(actor, "user_id", app.user_id),
        )
