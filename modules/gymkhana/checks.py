from __future__ import annotations

import os
import stat
from pathlib import Path

from django.conf import settings
from django.core.checks import Error, Warning  # noqa: A004


def check_upload_root(app_configs, **kwargs):
    root = Path(settings.GYMKHANA_UPLOAD_ROOT).expanduser()
    base = Path(settings.BASE_DIR).resolve()
    try:
        resolved = root.resolve()
    except OSError:
        resolved = root
    if resolved == base or base in resolved.parents:
        return [Error(
            f"GYMKHANA_UPLOAD_ROOT ({resolved}) is inside the project directory ({base}).",
            hint="Choose a persistent upload directory outside the repository.",
            id="gymkhana.files.E001",
        )]
    if resolved.is_dir():
        mode = os.stat(resolved).st_mode
        if mode & (stat.S_IROTH | stat.S_IXOTH):
            return [Warning(
                f"GYMKHANA_UPLOAD_ROOT ({resolved}) is accessible by other users.",
                hint="Restrict the upload directory to the application service account.",
                id="gymkhana.files.W001",
            )]
    return []
