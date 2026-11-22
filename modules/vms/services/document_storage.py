"""Private, fail-closed storage and validation for visitor identity documents."""

import hashlib
import logging
import os
import re
import socket
import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError

MAX_DOCUMENT_BYTES = 5 * 1024 * 1024
_ALLOWED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg"}
logger = logging.getLogger(__name__)


def _assert_safe_pdf(pdf, pikepdf):
    if len(pdf.pages) > 100:
        raise ValidationError("Identity PDF contains too many pages.")
    dangerous = {
        "/OpenAction",
        "/AA",
        "/JavaScript",
        "/JS",
        "/EmbeddedFiles",
        "/RichMedia",
        "/Launch",
        "/SubmitForm",
        "/ImportData",
    }
    for obj in pdf.objects:
        if isinstance(obj, pikepdf.Dictionary) and dangerous.intersection(str(key) for key in obj):
            raise ValidationError("PDF contains active or embedded content.")
        if isinstance(obj, pikepdf.Dictionary) and str(obj.get("/S", "")) in {
            "/JavaScript",
            "/Launch",
            "/SubmitForm",
            "/ImportData",
        }:
            raise ValidationError("PDF contains an active action.")
    for key in ("/OpenAction", "/AA", "/Names", "/JavaScript", "/EmbeddedFiles"):
        if key in pdf.Root:
            if key == "/Names":
                names = pdf.Root[key]
                if "/JavaScript" in names or "/EmbeddedFiles" in names:
                    raise ValidationError("PDF contains active or embedded content.")
            else:
                raise ValidationError("PDF contains active content.")


def _clean_pdf(data: bytes) -> bytes:
    # pikepdf rewrites the document structure; reject active content instead of
    # trying to preserve executable actions while normalising an identity scan.
    try:
        import pikepdf
    except ImportError as exc:  # configuration/deployment error: fail closed
        raise ValidationError("PDF sanitization is unavailable.") from exc
    from io import BytesIO

    try:
        with pikepdf.open(BytesIO(data)) as pdf:
            _assert_safe_pdf(pdf, pikepdf)
            # pikepdf's Dictionary-like document info does not implement
            # ``clear`` consistently across supported releases.
            for key in tuple(pdf.docinfo.keys()):
                del pdf.docinfo[key]
            output = BytesIO()
            pdf.save(
                output, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate
            )
            return output.getvalue()
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError("The PDF could not be safely decoded.") from exc


def validate_upload(upload):
    if not upload or upload.size <= 0 or upload.size > MAX_DOCUMENT_BYTES:
        raise ValidationError("Identity document must be between 1 byte and 5 MB.")
    suffix = Path(upload.name or "").suffix.casefold()
    if suffix not in _ALLOWED_SUFFIXES:
        raise ValidationError("Use a PDF, PNG, or JPEG identity document.")
    chunks = []
    total = 0
    for chunk in upload.chunks():
        total += len(chunk)
        if total > MAX_DOCUMENT_BYTES:
            raise ValidationError("Identity document exceeds the 5 MB limit.")
        chunks.append(chunk)
    data = b"".join(chunks)
    if data.startswith(b"%PDF-"):
        kind, mime = ".pdf", "application/pdf"
        data = _clean_pdf(data)
    elif data.startswith(b"\x89PNG\r\n\x1a\n"):
        kind, mime = ".png", "image/png"
    elif data.startswith(b"\xff\xd8\xff"):
        kind, mime = ".jpg", "image/jpeg"
    else:
        raise ValidationError("The uploaded document does not match an allowed file type.")
    if suffix not in {kind, ".jpeg" if kind == ".jpg" else kind}:
        raise ValidationError("The file extension does not match its content.")
    filename = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(upload.name).name)[:160]
    return data, filename or f"identity{kind}", mime


def save_upload(upload):
    data, filename, mime = validate_upload(upload)
    root = Path(settings.VMS_ID_UPLOAD_ROOT).resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    key = uuid.uuid4().hex
    target = root / key[:2] / key
    target.parent.mkdir(mode=0o700, exist_ok=True)
    os.chmod(target.parent, 0o700)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return {
        "storage_key": key,
        "filename": filename,
        "content_type": mime,
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "path": target,
    }


def remove_upload(storage_key):
    if not re.fullmatch(r"[0-9a-f]{32}", str(storage_key)):
        return
    target = Path(settings.VMS_ID_UPLOAD_ROOT).resolve() / storage_key[:2] / storage_key
    try:
        target.unlink(missing_ok=True)
    except OSError:
        # A failed cleanup is surfaced operationally by storage monitoring;
        # never convert a failed DB operation into a successful upload.
        logger.exception("Could not remove an orphaned VMS identity upload")


def upload_path(storage_key):
    if not re.fullmatch(r"[0-9a-f]{32}", str(storage_key)):
        raise ValueError("Invalid VMS document key")
    root = Path(settings.VMS_ID_UPLOAD_ROOT).resolve()
    path = (root / storage_key[:2] / storage_key).resolve(strict=True)
    if root not in path.parents or not path.is_file():
        raise FileNotFoundError("VMS document is unavailable")
    return path


def scan_with_clamav(storage_key):
    """Run clamd INSTREAM over its local Unix socket; unavailable means fail closed."""
    if not re.fullmatch(r"[0-9a-f]{32}", str(storage_key)):
        raise ValueError("Invalid VMS document key")
    path = upload_path(storage_key)
    socket_path = settings.VMS_CLAMD_SOCKET
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(30)
        client.connect(socket_path)
        client.sendall(b"zINSTREAM\0")
        with path.open("rb") as source:
            while chunk := source.read(64 * 1024):
                client.sendall(len(chunk).to_bytes(4, "big") + chunk)
        client.sendall(b"\0\0\0\0")
        response = client.recv(4096).decode("utf-8", "replace").strip("\0\r\n ")
    if response.endswith("OK"):
        return "clean", ""
    if "FOUND" in response:
        return "infected", response[:160]
    raise RuntimeError("ClamAV returned an indeterminate scan result")


def clamav_available(timeout=1):
    """Check that the configured local scanner is accepting protocol requests."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(timeout)
            client.connect(settings.VMS_CLAMD_SOCKET)
            client.sendall(b"zPING\0")
            return client.recv(64).strip(b"\0\r\n ") == b"PONG"
    except OSError:
        return False
