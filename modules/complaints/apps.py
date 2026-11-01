from django.apps import AppConfig
from django.core.checks import register


class ComplaintsConfig(AppConfig):
    name = "modules.complaints"
    label = "complaints"
    verbose_name = "Complaints"

    def ready(self):
        from modules.complaints.checks import check_configuration

        register(check_configuration)
