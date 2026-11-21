from django.apps import AppConfig


class SystemAdminConfig(AppConfig):
    name = "modules.system_admin"
    label = "system_admin"
    verbose_name = "System Administrator"

    def ready(self) -> None:
        pass
