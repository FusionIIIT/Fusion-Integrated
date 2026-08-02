"""Startup check for the upload root.

Where it points is a security property, not a preference, so CI fails on a bad
value rather than a person noticing.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path

from django.conf import settings
from django.core.checks import Error, Warning  # noqa: A004

UPLOADS_IN_REPO = "fusion.files.E001"
UPLOADS_WORLD_READABLE = "fusion.files.W001"


def check_upload_root(app_configs, **kwargs):
    """The upload root must sit outside the working tree — inside it, the
    files are one `git add -A` from being published."""
    errors = []
    root = Path(settings.PLACEMENT_UPLOAD_ROOT).expanduser()
    base = Path(settings.BASE_DIR).resolve()

    try:
        resolved = root.resolve()
    except OSError:                       # a path we cannot even resolve
        resolved = root

    if resolved == base or base in resolved.parents:
        errors.append(Error(
            f"PLACEMENT_UPLOAD_ROOT ({resolved}) is inside the project "
            f"directory ({base}).",
            hint="Uploaded documents are personal data. Point "
                 "PLACEMENT_UPLOAD_ROOT somewhere outside the repository, "
                 "such as ~/.local/share/fusion-integrated/uploads in "
                 "development or a managed volume in production.",
            id=UPLOADS_IN_REPO,
        ))

    if resolved.is_dir():
        mode = os.stat(resolved).st_mode
        if mode & (stat.S_IROTH | stat.S_IXOTH):
            errors.append(Warning(
                f"PLACEMENT_UPLOAD_ROOT ({resolved}) is readable by other "
                "users on this host.",
                hint="chmod 700 the directory. Individual files are written "
                     "0600, but a traversable parent leaks their names.",
                id=UPLOADS_WORLD_READABLE,
            ))

    return errors
