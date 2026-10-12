"""Django app configuration for ``modules.elm``."""

from django.apps import AppConfig


class ELMConfig(AppConfig):
    name = "modules.elm"
    label = "elm"
    verbose_name = "Employee Leave Management"

    def ready(self) -> None:
        super().ready()
