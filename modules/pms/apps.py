from django.apps import AppConfig
from django.core.checks import register


class PmsConfig(AppConfig):
    name = "modules.pms"
    label = "pms"
    verbose_name = "Patent Management System"

    def ready(self):
        from modules.pms.checks import check_pms_upload_root

        register(check_pms_upload_root)
