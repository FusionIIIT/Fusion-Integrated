"""Private complaint attachment storage outside the application tree."""

from __future__ import annotations

from pathlib import Path

from django.conf import settings


class CmsStorageError(Exception):
    pass


def path_for(storage_key: str) -> Path:
    if not storage_key or not storage_key.isalnum() or len(storage_key) != 32:
        raise CmsStorageError("Invalid CMS attachment key.")
    root = Path(settings.CMS_UPLOAD_ROOT).expanduser().resolve()
    target = (root / storage_key[:2] / storage_key[2:4] / storage_key).resolve()
    if root not in target.parents:
        raise CmsStorageError("Attachment path escapes CMS storage.")
    return target


def save(upload) -> tuple[str, int]:
    import uuid

    key = uuid.uuid4().hex
    target = path_for(key)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        size = _write_upload(upload, target)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return key, size


def _write_upload(upload, target):
    size = 0
    with target.open("wb") as stream:
        for chunk in upload.chunks():
            size += len(chunk)
            if size > settings.CMS_ATTACHMENT_MAX_BYTES:
                raise CmsStorageError("Attachment exceeds the configured size limit.")
            stream.write(chunk)
    return size


def open_file(storage_key):
    path = path_for(storage_key)
    if not path.is_file():
        raise CmsStorageError("Attachment is missing from private storage.")
    return path.open("rb")


def delete(storage_key):
    try:
        path_for(storage_key).unlink(missing_ok=True)
    except CmsStorageError:
        return
