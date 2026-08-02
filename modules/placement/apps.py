from django.apps import AppConfig
from django.core.checks import register


class PlacementConfig(AppConfig):
    name = "modules.placement"
    label = "placement"

    def ready(self):
        # PLACEMENT_UPLOAD_ROOT is this module's setting, so it owns the check.
        from core.files.checks import check_upload_root

        register(check_upload_root)
