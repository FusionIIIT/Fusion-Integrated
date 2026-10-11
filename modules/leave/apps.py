from django.apps import AppConfig
from django.core.checks import register


class LeaveConfig(AppConfig):
    name = "leave"
    label = "Leave Management"

    def ready(self):
        # Leave upload root is this module's setting, so it owns the check.
        from core.files.checks import check_leave_upload_root

        register(check_leave_upload_root)
