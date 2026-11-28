"""Documents are Google Drive links (ruling R1): parsed to a file id and rebuilt, never echoed."""
from __future__ import annotations

from core.api.exceptions import DomainError
from core.files import drive


def parse_link(raw: str | None, *, field: str, missing_code: str,
               missing_message: str, required: bool = True) -> drive.DriveRef | None:
    """A missing required link is "required file missing" (BR-GYM-018/019)."""
    if not (raw or "").strip():
        if not required:
            return None
        raise DomainError(missing_message, code=missing_code,
                          details=[{"field": field, "message": missing_message}])
    try:
        return drive.parse(raw)
    except drive.InvalidDriveLink as exc:
        raise DomainError(exc.message, code=exc.code,
                          details=[{"field": field, "message": exc.message}]) from exc
