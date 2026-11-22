from django.apps import AppConfig


class PmsConfig(AppConfig):
    name = "modules.pms"
    label = "pms"
    verbose_name = "Patent Management System"

    def ready(self):
        # Register module checks or signals if required
        pass
