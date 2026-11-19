"""Fail if evidence uploads could be committed with application code."""
from pathlib import Path

from django.conf import settings
from django.core.checks import Error, register


def check_iaa_upload_root(app_configs, **kwargs):
    root = Path(settings.IAA_UPLOAD_ROOT).expanduser().resolve()
    project = Path(settings.BASE_DIR).resolve()
    if root == project or project in root.parents:
        return [Error(
            f"IAA_UPLOAD_ROOT ({root}) is inside the project directory ({project}).",
            hint="Store IAA evidence outside the repository.",
            id="fusion.iaa.E001")]
    return []
