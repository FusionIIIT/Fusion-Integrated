import os
import stat
from pathlib import Path

from django.conf import settings
from django.core.checks import Error
from django.core.checks import Warning as CheckWarning


def check_pms_upload_root(app_configs, **kwargs):
    root = Path(settings.PMS_UPLOAD_ROOT).expanduser()
    base = Path(settings.BASE_DIR).resolve()
    resolved = root.resolve()
    if resolved == base or base in resolved.parents:
        return [
            Error(
                f"PMS_UPLOAD_ROOT ({resolved}) is inside the project directory.",
                hint="Store patent documents in a private managed volume outside the repository.",
                id="pms.files.E001",
            )
        ]
    if resolved.is_dir() and os.stat(resolved).st_mode & (stat.S_IROTH | stat.S_IXOTH):
        return [
            CheckWarning(
                f"PMS_UPLOAD_ROOT ({resolved}) is readable by other host users.",
                hint="Restrict the directory to the Fusion service account (mode 0700).",
                id="pms.files.W001",
            )
        ]
    return []
