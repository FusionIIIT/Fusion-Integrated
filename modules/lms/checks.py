"""LMS system checks for media upload root configuration."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from django.conf import settings
from django.core.checks import Error, Warning  # noqa: A004

LMS_UPLOADS_IN_REPO = "lms.files.E001"
LMS_UPLOADS_WORLD_READABLE = "lms.files.W001"


def check_lms_upload_root(app_configs, **kwargs):
    """The LMS MEDIA_ROOT must sit outside the repository working tree."""
    errors = []
    media_root = getattr(settings, "MEDIA_ROOT", None)
    if not media_root:
        return errors

    root = Path(media_root).expanduser()
    base = Path(settings.BASE_DIR).resolve()

    try:
        resolved = root.resolve()
    except OSError:
        resolved = root

    if resolved == base or base in resolved.parents:
        errors.append(
            Error(
                f"MEDIA_ROOT ({resolved}) is inside the project directory ({base}).",
                hint="Uploaded materials and submissions must sit outside the "
                "repository, such as ~/.local/share/fusion-integrated/media in "
                "development or a managed volume in production.",
                id=LMS_UPLOADS_IN_REPO,
            )
        )

    if resolved.is_dir():
        mode = os.stat(resolved).st_mode
        if mode & (stat.S_IROTH | stat.S_IXOTH):
            errors.append(
                Warning(
                    f"MEDIA_ROOT ({resolved}) is readable by other users on this host.",
                    hint="chmod 700 the directory. Individual files are written "
                    "0600, but a traversable parent leaks their names.",
                    id=LMS_UPLOADS_WORLD_READABLE,
                )
            )

    return errors
