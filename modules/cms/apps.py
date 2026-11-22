from pathlib import Path

from django.apps import AppConfig
from django.core.checks import Error, register


class CmsConfig(AppConfig):
    name = "modules.cms"
    label = "cms"
    verbose_name = "Complaint Management System"

    def ready(self):
        register(check_cms_settings)


def check_cms_settings(app_configs, **kwargs):
    from django.conf import settings

    problems = []
    if settings.CMS_CLOSURE_VERIFIER not in {"complainant", "supervisor"}:
        problems.append(
            Error("CMS_CLOSURE_VERIFIER must be complainant or supervisor.", id="cms.E001")
        )
    if settings.CMS_REOPENED_STATUS not in {"submitted", "in_progress"}:
        problems.append(
            Error("CMS_REOPENED_STATUS must be submitted or in_progress.", id="cms.E002")
        )
    if settings.CMS_ATTACHMENT_MAX_BYTES <= 0 or settings.CMS_ATTACHMENT_MAX_COUNT <= 0:
        problems.append(
            Error("CMS attachment byte and count limits must be positive.", id="cms.E003")
        )
    if not settings.CMS_ATTACHMENT_ALLOWED_EXTENSIONS or any(
        not ext.startswith(".") for ext in settings.CMS_ATTACHMENT_ALLOWED_EXTENSIONS
    ):
        problems.append(
            Error(
                "CMS_ATTACHMENT_ALLOWED_EXTENSIONS must contain extensions beginning with a dot.",
                id="cms.E004",
            )
        )
    upload_root = Path(settings.CMS_UPLOAD_ROOT).expanduser().resolve()
    base_dir = Path(settings.BASE_DIR).resolve()
    if upload_root == base_dir or base_dir in upload_root.parents:
        problems.append(Error("CMS_UPLOAD_ROOT must be outside the repository.", id="cms.E005"))
    return problems
