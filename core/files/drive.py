"""Google Drive link validation.

A submitted link is one a recruiter will click, so it is parsed down to a file
id and rebuilt — an echoed URL would make this field an open redirect.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

#: An allowlist, so a new Google property is added on purpose.
ALLOWED_HOSTS = frozenset({
    "drive.google.com",
    "docs.google.com",
})

#: Bounded, so a pathological string never reaches the database.
FILE_ID = re.compile(r"^[A-Za-z0-9_-]{10,200}$")

_PATH_ID = re.compile(
    r"^/(?:file|document|spreadsheets|presentation|forms)/d/([A-Za-z0-9_-]+)")
_FOLDER_ID = re.compile(r"^/(?:drive/)?folders/([A-Za-z0-9_-]+)")

MAX_URL_LENGTH = 500


class InvalidDriveLink(Exception):
    """Shown to the student, so it says what to paste instead."""

    def __init__(self, message: str, *, code: str):
        super().__init__(message)
        self.message = message
        self.code = code


@dataclass(frozen=True)
class DriveRef:
    file_id: str
    #: Rebuilt from the id, never the string the student submitted.
    url: str
    is_folder: bool


def _reject(message: str, code: str):
    raise InvalidDriveLink(message, code=code)


def parse(raw: str) -> DriveRef:
    """Validate a Drive link and return its canonical form."""
    raw = (raw or "").strip()
    if not raw:
        _reject("Paste the Google Drive link to your document.", "url_required")
    if len(raw) > MAX_URL_LENGTH:
        _reject("That link is too long to be a Drive link.", "url_too_long")

    try:
        parts = urlparse(raw)
    except ValueError:
        _reject("That does not look like a link.", "url_unparseable")

    if parts.scheme != "https":
        # `javascript:` and `data:` would execute in whoever clicked it.
        _reject("The link must start with https://.", "url_not_https")

    # `drive.google.com@evil.test` passes the allowlist but resolves to evil.test.
    if parts.username or parts.password or "@" in (parts.netloc or ""):
        _reject("That link is not a Google Drive link.", "url_not_drive")

    host = (parts.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        _reject("Only Google Drive links are accepted. Share the file from "
                "Drive and paste the link here.", "url_not_drive")

    folder = _FOLDER_ID.match(parts.path)
    if folder:
        _reject("That is a link to a folder. Share the document itself, not "
                "the folder it sits in.", "url_is_folder")

    file_id = None
    match = _PATH_ID.match(parts.path)
    if match:
        file_id = match.group(1)
    elif parts.path in ("/open", "/uc", "/file/d/", "/thumbnail"):
        ids = parse_qs(parts.query).get("id") or []
        file_id = ids[0] if ids else None

    if not file_id or not FILE_ID.match(file_id):
        _reject("That Drive link does not point at a file. Use Share → Copy "
                "link on the document.", "url_no_file_id")

    # Rebuilt, so query strings and fragments are dropped rather than stored.
    return DriveRef(
        file_id=file_id,
        url=f"https://drive.google.com/file/d/{file_id}/view",
        is_folder=False,
    )
