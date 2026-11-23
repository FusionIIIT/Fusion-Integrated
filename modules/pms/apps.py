from django.apps import AppConfig
from django.core.checks import register


class PmsConfig(AppConfig):
    name = "modules.pms"
    label = "pms"
    verbose_name = "Patent Management"

    def ready(self):
        from modules.pms import checks

        register(checks.check_upload_root)
        register(checks.check_scanner_backend)
