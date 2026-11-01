"""Document upload, validation, version management and malware boundary (BR-PMS-014..016)."""

from __future__ import annotations

import logging
from typing import Any

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from modules.pms.domain.constants import (
    SENSITIVITIES,
    SENSITIVITY_CONFIDENTIAL,
    STATUS_NEEDS_REVISION,
)
from modules.pms.domain.exceptions import ValidationError
from modules.pms.domain.rules import validate_document_file
from modules.pms.models import ApplicationDocument, PatentApplication
from modules.pms.services.audit import record_audit_event

log = logging.getLogger("fusion.pms.documents")


def verify_malware_boundary(file_bytes: bytes, filename: str) -> dict[str, Any]:
    """Verify document safety and record realistic malware scanning status (BR-PMS-016).

    Checks PDF magic bytes (%PDF-) and inspects for known malicious payloads.
    Acknowledges when external ClamAV daemon is uninstalled in the host environment.
    """
    if not file_bytes.startswith(b"%PDF-"):
        msg = "File does not have a valid PDF header signature."
        raise ValidationError(msg, rule_id="BR-PMS-014")

    # Basic heuristic check for suspicious embedded executable actions in PDF
    suspicious_tags = [b"/Launch", b"/EmbeddedFile", b"/AcroForm", b"/RichMedia"]
    found_tags = [tag.decode("ascii") for tag in suspicious_tags if tag in file_bytes]

    return {
        "engine": "internal_heuristic_verifier",
        "daemon_clamav_connected": False,
        "magic_bytes_verified": True,
        "suspicious_tags_found": found_tags,
        "is_clean": len(found_tags) == 0,
    }


@transaction.atomic
def upload_application_document(
    application: PatentApplication,
    uploaded_file: UploadedFile,
    document_type: str,
    title: str,
    uploaded_by_user_id: int,
    sensitivity: str = SENSITIVITY_CONFIDENTIAL,
) -> ApplicationDocument:
    """Upload and version an application document (BR-PMS-014, 015, 016, 082, 087)."""
    # 1. BR-PMS-087: Applicants may edit/upload revisions only while status is Needs Revision
    if application.user_id == uploaded_by_user_id and application.status not in (
        "draft",
        "resubmitted",
        STATUS_NEEDS_REVISION,
    ):
        msg = f"Uploads allowed only when status is 'needs_revision' ({application.status!r})."
        raise ValidationError(msg, rule_id="BR-PMS-087")

    # 2. Validate format (PDF) & size (<= 50MB) (BR-PMS-014, 015)
    validate_document_file(
        filename=uploaded_file.name,
        file_size=uploaded_file.size,
        mime_type=uploaded_file.content_type or "application/pdf",
    )

    if sensitivity not in SENSITIVITIES:
        raise ValidationError(f"Invalid sensitivity: {sensitivity}. Must be one of {SENSITIVITIES}")

    # 3. Read bytes & inspect malware boundary (BR-PMS-016)
    file_bytes = uploaded_file.read()
    uploaded_file.seek(0)
    scan_result = verify_malware_boundary(file_bytes, uploaded_file.name)

    if not scan_result["is_clean"]:
        msg = f"Malware scan flagged suspicious tags: {scan_result['suspicious_tags_found']}"
        raise ValidationError(msg, rule_id="BR-PMS-016")

    # 4. Automatic version numbering (BR-PMS-082)
    last_doc = (
        ApplicationDocument.objects.filter(application=application, document_type=document_type)
        .order_by("-version")
        .first()
    )
    version = (last_doc.version + 1) if last_doc else 1

    # 5. Create ApplicationDocument
    doc = ApplicationDocument.objects.create(
        application=application,
        document_type=document_type,
        title=title.strip() or uploaded_file.name,
        file=uploaded_file,
        file_size=uploaded_file.size,
        mime_type="application/pdf",
        sensitivity=sensitivity,
        version=version,
        uploaded_by_user_id=uploaded_by_user_id,
        is_malware_scanned=True,
        scan_details=scan_result,
    )

    # 6. Audit log
    record_audit_event(
        application=application,
        user_id=uploaded_by_user_id,
        actor_role="uploader",
        action_type="upload_document",
        details={
            "document_id": doc.id,
            "document_type": document_type,
            "version": version,
            "sensitivity": sensitivity,
        },
    )

    return doc
