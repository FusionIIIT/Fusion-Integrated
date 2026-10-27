from django.apps import AppConfig
from django.core.checks import register


class LeaveConfig(AppConfig):
    name = "modules.leave"
    label = "leave_management"

    def ready(self):
        # LEAVE_UPLOAD_ROOT is this module's setting, so it owns the check.
        from core.files.checks import check_upload_root

        register(check_upload_root)
