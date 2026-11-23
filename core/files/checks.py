"""Startup check for configured upload roots."""
from __future__ import annotations

import os
import stat
from pathlib import Path

from django.conf import settings
from django.core.checks import Error, Warning  # noqa: A004

UPLOADS_IN_REPO = "fusion.files.E001"
UPLOADS_WORLD_READABLE = "fusion.files.W001"


def check_upload_root(app_configs, **kwargs):
    """The upload root must sit outside the working tree to avoid publishing private data."""
    errors = []
    base = Path(settings.BASE_DIR).resolve()
    roots = []
    if getattr(settings, "PLACEMENT_UPLOAD_ROOT", None):
        roots.append(("PLACEMENT_UPLOAD_ROOT", settings.PLACEMENT_UPLOAD_ROOT))
    if getattr(settings, "MEDIA_ROOT", None):
        roots.append(("MEDIA_ROOT", settings.MEDIA_ROOT))

    for setting_name, path_val in roots:
        root = Path(path_val).expanduser()
        try:
            resolved = root.resolve()
        except OSError:
            resolved = root

        if resolved == base or base in resolved.parents:
            errors.append(Error(
                f"{setting_name} ({resolved}) is inside the project directory ({base}).",
                hint=f"Uploaded documents are personal data. Point {setting_name} somewhere "
                     "outside the repository, such as ~/.local/share/fusion-integrated/uploads "
                     "in development or a managed volume in production.",
                id=UPLOADS_IN_REPO,
            ))

        if resolved.is_dir():
            mode = os.stat(resolved).st_mode
            if mode & (stat.S_IROTH | stat.S_IXOTH):
                errors.append(Warning(
                    f"{setting_name} ({resolved}) is readable by other users on this host.",
                    hint="chmod 700 the directory. Individual files are written "
                         "0600, but a traversable parent leaks their names.",
                    id=UPLOADS_WORLD_READABLE,
                ))

    return errors
