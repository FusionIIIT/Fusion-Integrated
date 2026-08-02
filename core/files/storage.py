"""Read-only storage for documents attached before the move to Drive links.

Nothing writes here any more. Delete this module once no row carries a
`storage_key`.
"""
from __future__ import annotations

import os
import pathlib

from django.conf import settings


class StorageError(Exception):
    pass


def _root() -> pathlib.Path:
    return pathlib.Path(settings.PLACEMENT_UPLOAD_ROOT).expanduser()


def path_for(storage_key: str) -> pathlib.Path:
    """Absolute path for a key, refusing anything that escapes the root."""
    if not storage_key or "/" in storage_key or "\\" in storage_key \
            or storage_key.startswith("."):
        raise StorageError(f"Refusing a suspicious storage key: {storage_key!r}")

    root = _root().resolve()
    target = (root / storage_key[:2] / storage_key[2:4] / storage_key)
    resolved = pathlib.Path(os.path.normpath(target))
    if root not in resolved.parents:
        raise StorageError("Resolved path escapes the upload root.")
    return resolved


def open_stream(storage_key: str):
    path = path_for(storage_key)
    if not path.exists():
        raise StorageError(f"Missing file for key {storage_key!r}")
    return open(path, "rb")


def internal_url(storage_key: str) -> str | None:
    """The X-Accel-Redirect target, or None when the view streams it."""
    prefix = getattr(settings, "PLACEMENT_UPLOAD_INTERNAL_PREFIX", "")
    if not prefix:
        return None
    return f"{prefix.rstrip('/')}/{storage_key[:2]}/{storage_key[2:4]}/{storage_key}"
