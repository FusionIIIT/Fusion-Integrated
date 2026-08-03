"""Profile documents — attach, replace, remove (PC-UC-001).

A document is a Drive link. Nothing is stored here, so the byte-level checks
are gone; the authorisation model around reaching one is unchanged.
"""
from __future__ import annotations

import logging

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from core.files import drive, validators
from modules.placement.models import ProfileDocument, StudentProfile
from modules.placement.services import profiles as profile_service

log = logging.getLogger("fusion.placement.documents")

KINDS = {"resume", "certificate", "offer_letter", "other"}

MAX_DOCUMENTS_PER_PROFILE = 20


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

    profile, _ = StudentProfile.objects.get_or_create(user_id=user_id)

    if ProfileDocument.objects.filter(profile=profile, is_active=True).count() \
            >= MAX_DOCUMENTS_PER_PROFILE:
        raise ConflictError(
            f"You can keep at most {MAX_DOCUMENTS_PER_PROFILE} documents. "
            "Remove one before adding another.",
            code="too_many_documents")

    existing = ProfileDocument.objects.filter(
        profile=profile, is_active=True, drive_file_id=ref.file_id,
        kind=kind).first()
    if existing:
        return existing        # submitted twice, not two documents

    if kind == "resume":
        # Deactivated, not deleted: an application points at what it was sent with.
        ProfileDocument.objects.filter(
            profile=profile, kind="resume", is_active=True
        ).update(is_active=False)

    document = ProfileDocument.objects.create(
        profile=profile, user_id=user_id, kind=kind,
        title=(title or "").strip()[:160] or _default_title(kind),
        original_filename=validators.sanitise_filename(title or "",
                                                       fallback=""),
        drive_url=ref.url,
        drive_file_id=ref.file_id,
        storage_key=None,
    )

    # A resume is 25% of completeness — the difference between applying or not.
    profile_service.recompute(user_id=user_id)
    log.info("placement.document.linked user=%s kind=%s file=%s",
             user_id, kind, ref.file_id)
    return document


def _default_title(kind: str) -> str:
    return {"resume": "Resume", "certificate": "Certificate",
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
    profile_service.recompute(user_id=user_id)
