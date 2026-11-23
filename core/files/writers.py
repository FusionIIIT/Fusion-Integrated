"""Private byte uploads; callers authorize the parent resource before reading."""

import gzip
import hashlib
import io
import json
import os
import tarfile
import tempfile
import zipfile
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.checks import Error
from django.http import FileResponse

from core.api.exceptions import DomainError, NotFoundError
from core.files.validators import sanitise_filename

LIMITS = {"material": 25_000_000, "submission": 10_000_000}
TYPES = {
    ".pdf": "application/pdf",
    ".zip": "application/zip",
    ".tar.gz": "application/gzip",
    ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".ipynb": "application/x-ipynb+json",
}


def private_root():
    return Path(settings.PRIVATE_UPLOAD_ROOT).expanduser().resolve()


def check_private_upload_root(**kwargs):
    root = private_root()
    if root == Path(root.anchor) or root.is_relative_to(Path(settings.BASE_DIR).resolve()):
        return [
            Error(
                "PRIVATE_UPLOAD_ROOT must be outside the repository and web root.", id="files.E002"
            )
        ]
    static = Path(settings.STATIC_ROOT).resolve()
    if root.is_relative_to(static):
        return [Error("PRIVATE_UPLOAD_ROOT must be outside STATIC_ROOT.", id="files.E002")]
    return []


def _invalid():
    return DomainError(
        "Choose a valid PDF, ZIP, TAR.GZ, TXT, DOCX or IPYNB file with its matching extension.",
        code="UPLOAD_TYPE_REJECTED",
    )


def _sniff(raw, suffix):
    try:
        if suffix == ".pdf":
            if not raw.startswith(b"%PDF-"):
                raise _invalid()
        elif suffix in (".zip", ".docx"):
            if not raw.startswith(b"PK\x03\x04"):
                raise _invalid()
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                names = set(archive.namelist())
                if suffix == ".docx" and not {"[Content_Types].xml", "word/document.xml"} <= names:
                    raise _invalid()
        elif suffix == ".tar.gz":
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as zipped:
                header = zipped.read(512)
            tarfile.TarInfo.frombuf(header, "utf-8", "strict")
        else:
            text = raw.decode("utf-8")
            if "\x00" in text or text.lstrip().lower().startswith(
                ("<!doctype html", "<html", "<svg")
            ):
                raise _invalid()
            if suffix == ".ipynb":
                book = json.loads(text)
                if (
                    not isinstance(book, dict)
                    or not isinstance(book.get("cells"), list)
                    or (not isinstance(book.get("nbformat"), int))
                ):
                    raise _invalid()
    except (
        ValueError,
        UnicodeError,
        OSError,
        EOFError,
        tarfile.TarError,
        zipfile.BadZipFile,
        RecursionError,
    ) as exc:
        raise _invalid() from exc
    return TYPES[suffix]


def write_upload(upload, *, profile, namespace):
    """Validate bounded bytes, atomically persist, and return path-free metadata."""
    if check_private_upload_root():
        raise DomainError(
            "Ask an administrator to configure private upload storage before retrying.",
            code="UPLOAD_UNAVAILABLE",
        )
    if profile not in LIMITS or not namespace.replace("_", "").isalnum():
        raise ValueError("Invalid upload profile or namespace")
    name = Path(str(upload.name).replace("\\", "/")).name
    suffix = ".tar.gz" if name.lower().endswith(".tar.gz") else Path(name).suffix.lower()
    if suffix not in TYPES or not name or len(name) > 200:
        raise _invalid()
    name = sanitise_filename(name[: -len(suffix)])[:100] + suffix
    raw = bytearray()
    for chunk in upload.chunks():
        raw.extend(chunk)
        if len(raw) > LIMITS[profile]:
            raise DomainError(
                "Choose a smaller file within the displayed upload limit.", code="UPLOAD_TOO_LARGE"
            )
    mime = _sniff(bytes(raw), suffix)
    key = f"{namespace}/{uuid4().hex}{suffix}"
    root = private_root()
    folder = root / namespace
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    if folder.is_symlink() or not folder.resolve().is_relative_to(root):
        raise DomainError(
            "Try again later or ask an administrator to restore private upload storage.",
            code="UPLOAD_UNAVAILABLE",
        )
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=folder, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
        os.replace(temporary, root / key)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {
        "storage_key": key,
        "name": name,
        "mime_type": mime,
        "size": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _path(key):
    root = private_root()
    candidate = root / key
    if (
        Path(key).is_absolute()
        or ".." in Path(key).parts
        or (not candidate.resolve().is_relative_to(root))
        or candidate.is_symlink()
    ):
        raise NotFoundError()
    return candidate


def discard_upload(key):
    _path(key).unlink(missing_ok=True)


def stream_upload(key, *, name, mime_type):
    try:
        stream = _path(key).open("rb")
    except OSError as exc:
        raise NotFoundError(
            "Ask the file owner or administrator to restore or replace the unavailable file."
        ) from exc
    response = FileResponse(stream, as_attachment=True, filename=name, content_type=mime_type)
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    return response
