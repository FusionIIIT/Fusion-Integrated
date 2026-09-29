"""Profile documents — attach, replace, remove (PC-UC-001).

A document is a Drive link. Nothing is stored here, so the byte-level checks
are gone; the authorisation model around reaching one is unchanged.
"""
from __future__ import annotations

import logging

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from core.files import drive, validators
from modules.placement.models import ProfileDocument

log = logging.getLogger("fusion.placement.documents")

#: No resume: a student keeps one on the ERP portal, not a copy here.
KINDS = {"certificate", "offer_letter", "other"}

MAX_DOCUMENTS_PER_STUDENT = 20


@transaction.atomic
def attach_link(*, user_id: int, kind: str, url: str,
                title: str = "") -> ProfileDocument:
    """Record a Drive link. The URL is parsed to a file id and rebuilt."""
    if kind not in KINDS:
        raise ConflictError(f"Unknown document kind {kind!r}.", code="bad_kind")

    try:
        ref = drive.parse(url)
    except drive.InvalidDriveLink as exc:
        raise ConflictError(exc.message, code=exc.code) from exc

    if ProfileDocument.objects.filter(user_id=user_id, is_active=True).count() \
            >= MAX_DOCUMENTS_PER_STUDENT:
        raise ConflictError(
            f"You can keep at most {MAX_DOCUMENTS_PER_STUDENT} documents. "
            "Remove one before adding another.",
            code="too_many_documents")

    existing = ProfileDocument.objects.filter(
        user_id=user_id, is_active=True, drive_file_id=ref.file_id,
        kind=kind).first()
    if existing:
        return existing        # submitted twice, not two documents

    document = ProfileDocument.objects.create(
        user_id=user_id, kind=kind,
        title=(title or "").strip()[:160] or _default_title(kind),
        original_filename=validators.sanitise_filename(title or "",
                                                       fallback=""),
        drive_url=ref.url,
        drive_file_id=ref.file_id,
        storage_key=None,
    )

    log.info("placement.document.linked user=%s kind=%s file=%s",
             user_id, kind, ref.file_id)
    return document


def _default_title(kind: str) -> str:
    return {"certificate": "Certificate",
            "offer_letter": "Offer letter"}.get(kind, "Document")


@transaction.atomic
def remove(*, document_id: int, user_id: int) -> None:
    """Deactivate. The row stays — a student must not be able to blank out
    evidence a recruiter already reviewed."""
    document = ProfileDocument.objects.filter(
        pk=document_id, user_id=user_id, is_active=True).first()
    if document is None:
        raise NotFoundError("No such document.")
    document.is_active = False
    document.save(update_fields=["is_active", "updated_at"])
