"""Upload checks shared by every Gymkhana service that stores a file."""

from __future__ import annotations

from collections.abc import Sequence

from core.api.exceptions import BadRequestError
from modules.gymkhana.domain.exceptions import DomainError
from modules.gymkhana.domain.validation import validate_upload

HEAD_BYTES = 512


def check_upload(upload, extensions: Sequence[str]) -> None:
    """Refuse an unacceptable file before anything is stored."""
    head = upload.read(HEAD_BYTES)
    upload.seek(0)
    try:
        validate_upload(name=upload.name, size=upload.size, head=head, extensions=extensions)
    except DomainError as exc:
        raise BadRequestError(str(exc), code="invalid_file") from exc
