"""Uploading, versioning and serving documents (UC-PMS-019; BR-PMS-014..016, 082..087)."""
from __future__ import annotations

import hashlib
import os
import secrets
from pathlib import Path

from django.conf import settings
from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from core.files.validators import sanitise_filename
from modules.pms.domain import documents as d
from modules.pms.domain.errors import InvalidInput
from modules.pms.models import Document, DocumentVersion
from modules.pms.selectors import scoping
from modules.pms.services import audit, notifications
from modules.pms.services.base import lock, require, ruled
from modules.pms.services.scanning import ScannerUnavailable, configured, scan

P_UPLOAD = "pms.document.create"
P_SENSITIVITY = "pms.document.update"
P_READ = "pms.document.view"


def root() -> Path:
    return Path(settings.PMS_UPLOAD_ROOT).expanduser()


def path_for(storage_key: str) -> Path:
    """Refuse any key that could leave the upload root."""
    if not storage_key.isalnum():
        raise ValueError("unsafe storage key")
    return root() / storage_key[:2] / storage_key[2:4] / storage_key


def _store(uploaded) -> tuple[str, int, str, Path]:
    """Copy the upload to a private file, hashing and measuring the bytes actually received."""
    key = secrets.token_hex(16)
    target = path_for(key)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    digest, size = hashlib.sha256(), 0
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as out:
        for chunk in uploaded.chunks():
            size += len(chunk)
            if size >= d.MAX_BYTES:
                break
            digest.update(chunk)
            out.write(chunk)
    return key, size, digest.hexdigest(), target


@ruled
def upload(*, actor, pk: int, uploaded, kind: str = "", title: str = "",
           sensitivity: str = "", document_id: int | None = None) -> DocumentVersion:
    """Checks the bytes, scans them, then records the version; a refusal leaves no file behind."""
    require(actor, P_UPLOAD)
    if uploaded is None:
        raise InvalidInput("Choose a PDF file to upload.", code="file_required")
    name = sanitise_filename(getattr(uploaded, "name", "") or "", fallback="document.pdf")
    d.check_size(uploaded.size or 0)
    head = uploaded.read(len(d.PDF_MAGIC))
    uploaded.seek(0)
    d.check_pdf(head, name)
    if document_id is None:
        d.check_kind(kind)
        d.check_sensitivity(sensitivity)
        clean_title = (title or "").strip()
        if not clean_title or len(clean_title) > 200:
            raise InvalidInput("Give the document a title of at most 200 characters.",
                               code="title_required")
    app = scoping.applications_for(actor).filter(pk=pk).first()
    if app is None:
        raise NotFoundError("No such application.", code="not_found")
    _may_upload(actor, app)
    if configured() is not None:
        raise ScannerUnavailable()
    key, size, sha, path = _store(uploaded)
    try:
        d.check_size(size)
        scanner = scan(path)
        version = _record(actor, pk, document_id, kind, clean_title if document_id is None
                          else "", sensitivity, key, name, size, sha, scanner)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return version


def _record(actor, pk, document_id, kind, title, sensitivity, key, name, size, sha, scanner):
    """Lock, check again, number the version and make it current, all in one transaction."""
    with transaction.atomic():
        app = lock(scoping.applications_for(actor), pk)
        _may_upload(actor, app)
        if document_id is None:
            doc = Document.objects.create(application=app, kind=kind, title=title,
                                          sensitivity=sensitivity,
                                          created_by_user_id=actor.user_id)
        else:
            doc = (Document.objects.select_for_update()
                   .filter(pk=document_id, application=app).first())
            if doc is None:
                raise NotFoundError("No such document.", code="not_found")
        highest = doc.versions.order_by("-number").values_list("number", flat=True).first()
        doc.versions.filter(is_current=True).update(is_current=False)
        version = DocumentVersion.objects.create(
            document=doc, number=d.next_version(highest), storage_key=key, original_name=name,
            size_bytes=size, sha256=sha, scanner=scanner, uploaded_by_user_id=actor.user_id)
        audit.record(actor, "document.uploaded", application=app, obj=version,
                     details={"document_id": doc.pk, "number": version.number,
                              "sensitivity": doc.sensitivity})
        _notify(app, doc, version, actor)
    return version


def _may_upload(actor, app) -> None:
    if not d.may_upload(scoping.relations(actor, app), app.status):
        raise PermissionDeniedError(
            f"Documents cannot be added by you while the application is "
            f"{app.status.replace('_', ' ')}.", code="upload_not_allowed")


def _notify(app, doc, version, actor) -> None:
    """PMS-AFR-203 / 204: the other parties working on the application hear about it."""
    attorney = app.attorney_assignments.filter(status="accepted").first()
    recipients = {app.applicant_user_id, getattr(attorney, "attorney_user_id", None)}
    recipients.discard(actor.user_id)
    words = "A new document" if version.number == 1 else f"Version {version.number}"
    notifications.enqueue_many(
        topic="document.updated", key=f"document:{version.pk}", recipients=sorted(
            r for r in recipients if r is not None),
        subject=f"Document updated on {app.reference or 'your draft'}",
        body=f"{words} of '{doc.title}' was uploaded to {app.reference or 'the draft'}.")


@ruled
def set_sensitivity(*, actor, document_id: int, sensitivity: str) -> Document:
    """Ruling C16: the applicant chooses at upload, and PCC_ADMIN may change it later."""
    require(actor, P_SENSITIVITY)
    d.check_sensitivity(sensitivity)
    doc = Document.objects.filter(pk=document_id,
                                  application__in=scoping.applications_for(actor)).first()
    if doc is None:
        raise NotFoundError("No such document.", code="not_found")
    with transaction.atomic():
        doc = Document.objects.select_for_update().get(pk=document_id)
        if doc.sensitivity == sensitivity:
            raise ConflictError("The document already has that sensitivity.",
                                code="unchanged")
        frm, doc.sensitivity = doc.sensitivity, sensitivity
        doc.save(update_fields=["sensitivity", "updated_at"])
        audit.record(actor, "document.sensitivity", application=doc.application, obj=doc,
                     frm=frm, to=sensitivity)
    return doc


def open_version(*, actor, version_id: int):
    """The file to stream, after scope and sensitivity checks; the download is audited."""
    require(actor, P_READ)
    version = scoping.version_for(actor, version_id)
    if version is None:
        raise NotFoundError("No such document.", code="not_found")
    path = path_for(version.storage_key)
    if not path.exists():
        raise NotFoundError("The stored file is missing; ask the PCC_ADMIN.",
                            code="file_missing")
    audit.record(actor, "document.downloaded", application=version.document.application,
                 obj=version)
    return version, path.open("rb")
