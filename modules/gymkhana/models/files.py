"""Private storage for uploaded club documents."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateStorage(FileSystemStorage):
    """Files outside the repository and web root, reachable only through a scoped view."""

    def __init__(self):
        super().__init__(file_permissions_mode=0o600, directory_permissions_mode=0o700)

    @property
    def base_location(self) -> str:
        # Under the platform's checked upload root, read per call so it follows the settings.
        return str(Path(settings.PLACEMENT_UPLOAD_ROOT).expanduser() / "gymkhana")

    @property
    def location(self) -> str:
        return os.path.abspath(self.base_location)

    def url(self, name):
        raise ValueError("Gymkhana files have no public URL.")


def _key(folder: str, filename: str) -> str:
    return f"{folder}/{uuid.uuid4().hex}{Path(filename).suffix.lower()[:10]}"


def poster_key(instance, filename: str) -> str:
    return _key("posters", filename)


def budget_key(instance, filename: str) -> str:
    return _key("budgets", filename)


def report_key(instance, filename: str) -> str:
    return _key("reports", filename)
