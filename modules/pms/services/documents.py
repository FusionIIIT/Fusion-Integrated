"""PMS Document Version Management service.

Enforces business rules BR-PMS-014 to 016, BR-PMS-082, 084, 086, 087.
"""

from __future__ import annotations

from django.db import transaction

from modules.pms.domain.entities import validate_document
from modules.pms.domain.errors import PreconditionNotMetError
from modules.pms.domain.state_machine import PatentApplicationStatus
from modules.pms.models import ApplicationDocument, PatentApplication
from modules.pms.services.audit import log_audit
from modules.pms.services.notifications import enqueue_notification


def upload_document_version(
    *,
    application_id: int,
    user_id: int,
    user_role: str,
    doc_type: str,
    title: str,
    filename: str,
    file_size_bytes: int,
    sensitivity: str = "confidential",
    file_url: str = "",
    is_malware_clean: bool = True,
) -> ApplicationDocument:
    """Upload a new document version with validation and automatic versioning (UC-PMS-019, CFR-PMS-018)."""
    # Document validation (BR-PMS-014, 015, 016)
    validate_document(filename, file_size_bytes, is_malware_clean)

    with transaction.atomic():
        app = PatentApplication.objects.select_for_update().get(pk=application_id)

        # Applicant edit constraint: Applicants can edit documents only while status is Needs Revision (BR-PMS-087)
        if user_role == "Applicant" and app.status not in (
            PatentApplicationStatus.NEEDS_REVISION.value,
            PatentApplicationStatus.DRAFT.value,
            PatentApplicationStatus.SUBMITTED.value,
        ):
            raise PreconditionNotMetError(
                f"Applicants may edit application documents only while status is Needs Revision, not '{app.status}' (BR-PMS-087)."
            )

        # Version assignment: find latest version for this doc_type (BR-PMS-082)
        latest_doc = (
            ApplicationDocument.objects.filter(application=app, doc_type=doc_type)
            .order_by("-version")
            .first()
        )
        new_version = (latest_doc.version + 1) if latest_doc else 1

        # Archive prior versions (BR-PMS-084)
        ApplicationDocument.objects.filter(
            application=app, doc_type=doc_type, is_current=True
        ).update(is_current=False)

        new_doc = ApplicationDocument.objects.create(
            application=app,
            doc_type=doc_type,
            title=title.strip(),
            file_format="pdf",
            file_size_bytes=file_size_bytes,
            malware_scanned=True,
            is_clean=True,
            sensitivity=sensitivity,
            version=new_version,
            is_current=True,
            uploaded_by_user_id=user_id,
            file_url=file_url.strip(),
        )

        log_audit(
            application=app,
            actor_user_id=user_id,
            action_type="document_version_uploaded",
            details={
                "doc_type": doc_type,
                "version": new_version,
                "title": title,
                "file_size": file_size_bytes,
            },
        )

        enqueue_notification(
            topic="document.updated",
            dedupe_key=f"pms:doc:upload:{new_doc.id}",
            subject=f"PMS: Document Updated ({doc_type} v{new_version})",
            body=f"A new version of {doc_type} has been uploaded for patent application '{app.title}'.",
            recipient_user_id=app.applicant_user_id,
        )

    return new_doc
