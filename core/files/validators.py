"""Filename sanitisation.

All that survives of the upload validation — documents are Drive links now, so
there are no bytes to check. A title still reaches a browser and an email.
"""
from __future__ import annotations

import re
import unicodedata

# Reaches a Content-Disposition header, so separators and controls go.
_UNSAFE = re.compile(r"[^A-Za-z0-9._ -]")


def sanitise_filename(name: str, *, fallback: str = "upload") -> str:
    """Safe in a header, where a newline would be response-splitting."""
    name = unicodedata.normalize("NFKD", name or "")
    name = name.replace("\\", "/").split("/")[-1]      # drop any path
    name = _UNSAFE.sub("_", name).strip(" .")
    # A leading dot would make it hidden; a name of only dots is nothing.
    if not name or set(name) <= {".", "_", " "}:
        name = fallback
    return name[:120]
