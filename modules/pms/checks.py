"""Startup checks for the two settings whose value is a security property."""
from __future__ import annotations

import os
import stat
from pathlib import Path

from django.conf import settings
from django.core.checks import Error, Warning  # noqa: A004

UPLOADS_IN_REPO = "pms.E001"
DEV_SCANNER_IN_PRODUCTION = "pms.E002"
UNKNOWN_SCANNER = "pms.E003"
UPLOADS_WORLD_READABLE = "pms.W001"


def upload_root_problem() -> str | None:
    """For readiness: what is wrong with the upload folder, as an instruction, or None."""
    root = Path(settings.PMS_UPLOAD_ROOT).expanduser()
    if any(e.id == UPLOADS_IN_REPO for e in check_upload_root(None)):
        return f"PMS_UPLOAD_ROOT ({root}) is inside the repository; point it elsewhere."
    try:
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError:
        return f"PMS_UPLOAD_ROOT ({root}) cannot be created; check its parent's permissions."
    if os.stat(root).st_mode & (stat.S_IROTH | stat.S_IXOTH):
        return f"PMS_UPLOAD_ROOT ({root}) is readable by other users; chmod 700 it."
    return None


def check_upload_root(app_configs, **kwargs):
    """Patent documents are confidential, so their folder sits outside the working tree."""
    errors = []
    root = Path(settings.PMS_UPLOAD_ROOT).expanduser()
    base = Path(settings.BASE_DIR).resolve()
    try:
        resolved = root.resolve()
    except OSError:
        resolved = root
    if resolved == base or base in resolved.parents:
        errors.append(Error(
            f"PMS_UPLOAD_ROOT ({resolved}) is inside the project directory ({base}).",
            hint="Point PMS_UPLOAD_ROOT outside the repository, such as "
                 "~/.local/share/fusion-integrated/pms-uploads.",
            id=UPLOADS_IN_REPO))
    if resolved.is_dir() and os.stat(resolved).st_mode & (stat.S_IROTH | stat.S_IXOTH):
        errors.append(Warning(
            f"PMS_UPLOAD_ROOT ({resolved}) is readable by other users on this host.",
            hint="chmod 700 the directory.", id=UPLOADS_WORLD_READABLE))
    return errors


def check_scanner_backend(app_configs, **kwargs):
    """The development scanner accepts nearly everything, so it never runs with DEBUG off."""
    backend = settings.PMS_MALWARE_SCANNER
    if backend not in ("clamd", "development"):
        return [Error(f"PMS_MALWARE_SCANNER is '{backend}'.",
                      hint="Use 'clamd' (production) or 'development' (DEBUG only).",
                      id=UNKNOWN_SCANNER)]
    if backend == "development" and not settings.DEBUG:
        return [Error("PMS_MALWARE_SCANNER is 'development' while DEBUG is off.",
                      hint="Set PMS_MALWARE_SCANNER=clamd and PMS_CLAMD_SOCKET.",
                      id=DEV_SCANNER_IN_PRODUCTION)]
    return []
