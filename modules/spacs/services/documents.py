"""Document handling service (CFR-SPACS-004, BR-SPACS-003, BR-SPACS-016)."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.spacs.models import ApplicationDocument, ScholarshipApplication
from modules.spacs.services.audit import record_audit_event


def attach_document(
    *,
    application_id: int,
    student_user_id: int,
    doc_type: str,
    title: str,
    file_url: str,
    valid_until=None,
    actor,
) -> ApplicationDocument:
    app = ScholarshipApplication.objects.filter(pk=application_id).first()
    if app is None:
        raise NotFoundError("Application not found.")

    if app.student_user_id != student_user_id:
        raise PermissionDeniedError("Cannot attach document to another student's application.")

    if app.status not in ["draft", "submitted", "correction_required"]:
        raise ConflictError(f"Cannot upload documents when application is in {app.status} status.")

    doc = ApplicationDocument.objects.create(
        application=app,
        student_user_id=student_user_id,
        doc_type=doc_type,
        title=title,
        file_url=file_url,
        valid_until=valid_until,
        verification_status="pending",
    )
    return doc


def reuse_document(
    *,
    application_id: int,
    student_user_id: int,
    source_doc_id: int,
    actor,
) -> ApplicationDocument:
    """Reuses a previously uploaded document if still valid (BR-SPACS-003)."""
    app = ScholarshipApplication.objects.filter(pk=application_id).first()
    if app is None:
        raise NotFoundError("Application not found.")

    if app.student_user_id != student_user_id:
        raise PermissionDeniedError("Ownership mismatch.")

    source_doc = ApplicationDocument.objects.filter(pk=source_doc_id, student_user_id=student_user_id).first()
    if source_doc is None:
        raise NotFoundError("Reusable document not found.")

    # BR-SPACS-003: check validity & reject if previously rejected
    if source_doc.verification_status == "rejected":
        raise ConflictError(
            f"Cannot reuse document '{source_doc.title}' because it was previously rejected.",
            code="document_rejected",
        )

    today = timezone.now().date()
    if source_doc.valid_until and source_doc.valid_until < today:
        raise ConflictError(
            f"Document '{source_doc.title}' expired on {source_doc.valid_until} and cannot be reused.",
            code="document_expired",
        )

    doc = ApplicationDocument.objects.create(
        application=app,
        student_user_id=student_user_id,
        doc_type=source_doc.doc_type,
        title=f"Reused: {source_doc.title}",
        file_url=source_doc.file_url,
        valid_until=source_doc.valid_until,
        is_reused=True,
        reused_from_doc_id=source_doc.id,
        verification_status="verified" if source_doc.verification_status == "verified" else "pending",
    )
    return doc


def verify_document(
    *,
    document_id: int,
    status: str,
    notes: str = "",
    actor,
) -> ApplicationDocument:
    """Authorized reviewer records document verification outcome (BR-SPACS-016)."""
    if actor is None or not (actor.has_permission("spacs.application.review") or actor.has_permission("spacs.application.approve")):
        raise PermissionDeniedError("Permission denied.")

    doc = ApplicationDocument.objects.select_related("application").filter(pk=document_id).first()
    if doc is None:
        raise NotFoundError("Document not found.")

    if status not in ["verified", "rejected"]:
        raise ConflictError("Status must be 'verified' or 'rejected'.")

    with transaction.atomic():
        doc.verification_status = status
        doc.verification_notes = notes
        doc.verified_by_user_id = getattr(actor, "user_id", None)
        doc.verified_at = timezone.now()
        doc.save(update_fields=["verification_status", "verification_notes", "verified_by_user_id", "verified_at", "updated_at"])

        record_audit_event(
            actor_user_id=getattr(actor, "user_id", None),
            actor_role="spacs_assistant",
            action="document.verified",
            entity_type="application_document",
            entity_id=str(doc.id),
            details={"status": status, "doc_type": doc.doc_type, "application_id": doc.application_id},
        )
        return doc
