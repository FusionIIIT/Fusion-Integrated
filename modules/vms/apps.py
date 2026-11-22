from pathlib import Path

from django.apps import AppConfig
from django.conf import settings
from django.core.checks import Error, Tags, register


class VmsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.vms"
    label = "vms"

    def ready(self):
        @register(Tags.security, deploy=True)
        def check_vms_private_storage(app_configs, **kwargs):
            del app_configs, kwargs
            root = Path(settings.VMS_ID_UPLOAD_ROOT).resolve()
            base = Path(settings.BASE_DIR).resolve()
            placement = Path(settings.PLACEMENT_UPLOAD_ROOT).resolve()
            errors = []
            if root == base or base in root.parents:
                errors.append(
                    Error(
                        "VMS identity files must be stored outside the application tree.",
                        id="vms.E001",
                    )
                )
            if root == placement or root in placement.parents or placement in root.parents:
                errors.append(
                    Error("VMS identity storage must not share Placement storage.", id="vms.E002")
                )
            if not settings.DEBUG and not str(root).startswith("/var/lib/fusion/"):
                errors.append(
                    Error(
                        "Production VMS identity storage must be under /var/lib/fusion/.",
                        id="vms.E003",
                    )
                )
            from modules.vms.services.document_storage import clamav_available

            if not settings.DEBUG and not clamav_available():
                errors.append(
                    Error(
                        "Production VMS malware-scanner socket is unavailable.",
                        hint="Install and start ClamAV clamd and configure VMS_CLAMD_SOCKET.",
                        id="vms.E004",
                    )
                )
            if not settings.DEBUG and not settings.VMS_PUBLIC_BASE_URL.startswith("https://"):
                errors.append(
                    Error("Production visitor portal URLs must use HTTPS.", id="vms.E005")
                )
            return errors
